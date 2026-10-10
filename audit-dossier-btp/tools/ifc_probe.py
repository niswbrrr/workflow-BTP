#!/usr/bin/env python3
"""Sonde IFC (STEP physique, IFC2x3 / IFC4) en bibliothèque standard.

Usage :
  python ifc_probe.py --fichier <maquette.ifc> --travail <_travail> [--doc-id D007]

Ce que l'outil lit réellement (et rien d'autre) :
  - en-tête (schéma, application d'origine, date) ;
  - nombre d'entités par type ; niveaux (IfcBuildingStorey) ;
  - éléments constructifs : GlobalId, nom, tag, niveau de rattachement ;
  - quantités EXPLICITES (IfcElementQuantity : surfaces, longueurs, volumes, nombres, poids) ;
  - noms des jeux de propriétés et propriétés simples (IfcPropertySingleValue) ;
  - références de classification, unités SI déclarées.
Limites : aucun calcul géométrique ; une quantité absente de la maquette reste absente ;
les éléments sans quantité sont comptés et signalés.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from btp_common import journal, print_summary, save_json  # noqa: E402

ELEMENTS = {"IFCWALL", "IFCWALLSTANDARDCASE", "IFCSLAB", "IFCBEAM", "IFCCOLUMN", "IFCWINDOW", "IFCDOOR",
            "IFCROOF", "IFCSTAIR", "IFCSTAIRFLIGHT", "IFCRAMP", "IFCRAILING", "IFCCOVERING", "IFCCURTAINWALL",
            "IFCPLATE", "IFCMEMBER", "IFCFOOTING", "IFCPILE", "IFCBUILDINGELEMENTPROXY", "IFCSPACE",
            "IFCFLOWTERMINAL", "IFCFLOWSEGMENT", "IFCFLOWFITTING", "IFCDUCTSEGMENT", "IFCPIPESEGMENT",
            "IFCSANITARYTERMINAL", "IFCAIRTERMINAL", "IFCLIGHTFIXTURE", "IFCOUTLET", "IFCELECTRICAPPLIANCE",
            "IFCCABLECARRIERSEGMENT", "IFCOPENINGELEMENT"}
QTY_TYPES = {"IFCQUANTITYAREA": 3, "IFCQUANTITYLENGTH": 3, "IFCQUANTITYVOLUME": 3, "IFCQUANTITYCOUNT": 3,
             "IFCQUANTITYWEIGHT": 3}
ENT_RE = re.compile(r"^#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\)\s*$", re.S)


def split_statements(data: str):
    out, buf, in_str = [], [], False
    i = 0
    while i < len(data):
        ch = data[i]
        if ch == "'":
            if in_str and i + 1 < len(data) and data[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_str = not in_str
        if ch == ";" and not in_str:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    return out


def decode_str(s: str) -> str:
    s = s.replace("''", "'")
    s = re.sub(r"\\X2\\([0-9A-F]+)\\X0\\",
               lambda m: "".join(chr(int(m.group(1)[k:k + 4], 16)) for k in range(0, len(m.group(1)), 4)), s)
    s = re.sub(r"\\X\\([0-9A-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("latin-1"), s)
    return s


def parse_args(s: str):
    pos = 0

    def value():
        nonlocal pos
        while pos < len(s) and s[pos] in " \r\n\t":
            pos += 1
        if pos >= len(s):
            return None
        ch = s[pos]
        if ch == "'":
            j = pos + 1
            buf = []
            while j < len(s):
                if s[j] == "'":
                    if j + 1 < len(s) and s[j + 1] == "'":
                        buf.append("''")
                        j += 2
                        continue
                    break
                buf.append(s[j])
                j += 1
            pos = j + 1
            return decode_str("".join(buf))
        if ch == "(":
            pos += 1
            items = []
            while True:
                while pos < len(s) and s[pos] in " \r\n\t,":
                    if s[pos] == ",":
                        pass
                    pos += 1
                if pos < len(s) and s[pos] == ")":
                    pos += 1
                    return items
                items.append(value())
                while pos < len(s) and s[pos] in " \r\n\t":
                    pos += 1
                if pos < len(s) and s[pos] == ",":
                    pos += 1
        if ch == "#":
            m = re.match(r"#(\d+)", s[pos:])
            pos += len(m.group(0))
            return ("ref", int(m.group(1)))
        if ch == ".":
            j = s.index(".", pos + 1)
            v = s[pos + 1:j]
            pos = j + 1
            return ("enum", v)
        if ch in "$*":
            pos += 1
            return None
        m = re.match(r"[A-Z][A-Z0-9_]*\s*\(", s[pos:])
        if m:  # valeur typée : IFCLABEL('x')
            pos += len(m.group(0)) - 1
            inner = value()
            return inner[0] if isinstance(inner, list) and len(inner) == 1 else inner
        m = re.match(r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?", s[pos:])
        if m:
            pos += len(m.group(0))
            txt = m.group(0)
            return float(txt) if any(c in txt for c in ".eE") else int(txt)
        pos += 1
        return None

    items = []
    while pos < len(s):
        items.append(value())
        while pos < len(s) and s[pos] in " \r\n\t":
            pos += 1
        if pos < len(s) and s[pos] == ",":
            pos += 1
        else:
            break
    return items


def refs(v):
    if isinstance(v, tuple) and v[0] == "ref":
        return [v[1]]
    if isinstance(v, list):
        return [x[1] for x in v if isinstance(x, tuple) and x[0] == "ref"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fichier", required=True)
    ap.add_argument("--travail", required=True)
    ap.add_argument("--doc-id", default="IFC")
    a = ap.parse_args()
    path = Path(a.fichier).expanduser().resolve()
    work = Path(a.travail).expanduser().resolve()
    try:
        text = path.read_text(encoding="latin-1")
    except OSError as exc:
        print_summary({"statut": "echec", "outil": "ifc_probe", "erreur": str(exc)})
        return 0
    if "ISO-10303-21" not in text[:200]:
        print_summary({"statut": "echec", "outil": "ifc_probe",
                       "erreur": "fichier non STEP (IFC-XML / IFC-ZIP non pris en charge)"})
        return 0

    header = text.split("ENDSEC;", 1)[0]
    schema = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", header)
    fname = re.search(r"FILE_NAME\s*\((.*?)\);", header, re.S)
    data = text.split("DATA;", 1)[1].rsplit("ENDSEC;", 1)[0] if "DATA;" in text else ""
    ents = {}
    errors = 0
    for st in split_statements(data):
        m = ENT_RE.match(st)
        if not m:
            continue
        try:
            ents[int(m.group(1))] = (m.group(2), parse_args(m.group(3)))
        except Exception:
            errors += 1
    counts = Counter(t for t, _ in ents.values())

    def name_of(eid):
        t, args = ents.get(eid, (None, []))
        return args[2] if len(args) > 2 and isinstance(args[2], str) else None

    storeys = {eid: {"nom": args[2] if len(args) > 2 else None,
                     "altitude": args[9] if len(args) > 9 and isinstance(args[9], (int, float)) else None}
               for eid, (t, args) in ents.items() if t == "IFCBUILDINGSTOREY"}
    elem_storey = {}
    elem_qty = defaultdict(dict)
    elem_psets = defaultdict(dict)
    elem_class = defaultdict(list)
    for eid, (t, args) in ents.items():
        if t == "IFCRELCONTAINEDINSPATIALSTRUCTURE" and len(args) >= 6:
            st_ref = refs(args[5])
            for e in refs(args[4]):
                if st_ref:
                    elem_storey[e] = st_ref[0]
        elif t == "IFCRELDEFINESBYPROPERTIES" and len(args) >= 6:
            pdef = refs(args[5])
            if not pdef or pdef[0] not in ents:
                continue
            pt, pargs = ents[pdef[0]]
            for e in refs(args[4]):
                if pt == "IFCELEMENTQUANTITY":
                    for q in refs(pargs[5] if len(pargs) > 5 else []):
                        qt, qargs = ents.get(q, (None, []))
                        if qt in QTY_TYPES and len(qargs) > 3:
                            elem_qty[e][f"{qargs[0]}"] = qargs[3]
                elif pt == "IFCPROPERTYSET":
                    props = {}
                    for pr in refs(pargs[4] if len(pargs) > 4 else []):
                        prt, prargs = ents.get(pr, (None, []))
                        if prt == "IFCPROPERTYSINGLEVALUE" and prargs:
                            props[prargs[0]] = prargs[2] if len(prargs) > 2 else None
                    elem_psets[e][pargs[2] if len(pargs) > 2 else f"#{pdef[0]}"] = props
        elif t == "IFCRELASSOCIATESCLASSIFICATION" and len(args) >= 6:
            cref = refs(args[5])
            if cref and cref[0] in ents:
                ct, cargs = ents[cref[0]]
                label = " ".join(str(x) for x in cargs[:3] if isinstance(x, str))
                for e in refs(args[4]):
                    elem_class[e].append(label)
    units = [f"{(args[2] or ('', ''))[1] if isinstance(args[2], tuple) else ''}{(args[3] or ('', ''))[1]}"
             for t, args in ents.values() if t == "IFCSIUNIT" and len(args) > 3 and isinstance(args[3], tuple)]

    elements = []
    for eid, (t, args) in sorted(ents.items()):
        if t not in ELEMENTS:
            continue
        rec = {"id": f"#{eid}", "type": t, "global_id": args[0] if args and isinstance(args[0], str) else None,
               "nom": args[2] if len(args) > 2 and isinstance(args[2], str) else None,
               "tag": args[7] if len(args) > 7 and isinstance(args[7], str) else None,
               "niveau": storeys.get(elem_storey.get(eid), {}).get("nom"),
               "quantites": elem_qty.get(eid, {}), "jeux_proprietes": elem_psets.get(eid, {}),
               "classification": elem_class.get(eid, [])}
        if t in ("IFCWINDOW", "IFCDOOR") and len(args) > 9:
            rec["hauteur_hors_tout"] = args[8] if isinstance(args[8], (int, float)) else None
            rec["largeur_hors_tout"] = args[9] if isinstance(args[9], (int, float)) else None
        elements.append(rec)

    sums = defaultdict(lambda: defaultdict(float))
    for e in elements:
        for qn, qv in e["quantites"].items():
            if isinstance(qv, (int, float)):
                sums[e["type"]][qn] += qv
    by_type = Counter(e["type"] for e in elements if e["type"] != "IFCOPENINGELEMENT")
    no_qty = Counter(e["type"] for e in elements if not e["quantites"] and e["type"] != "IFCOPENINGELEMENT")
    no_name = sum(1 for e in elements if not e["nom"])
    no_storey = sum(1 for e in elements if not e["niveau"] and e["type"] != "IFCOPENINGELEMENT")

    result = {"outil": "ifc_probe", "fichier": str(path), "doc_id": a.doc_id,
              "schema": schema.group(1) if schema else None,
              "en_tete_file_name": fname.group(1).strip()[:400] if fname else None,
              "unites_si_declarees": sorted(set(units)), "nb_entites": len(ents), "erreurs_analyse": errors,
              "entites_par_type": dict(counts.most_common()), "niveaux": list(storeys.values()),
              "elements_par_type": dict(by_type), "elements_sans_quantite": dict(no_qty),
              "elements_sans_nom": no_name, "elements_sans_niveau": no_storey,
              "sommes_quantites_par_type": {t: {k: round(v, 3) for k, v in q.items()} for t, q in sums.items()},
              "elements": elements[:3000],
              "limites": ["quantités lues uniquement dans les IfcElementQuantity explicites (aucun calcul géométrique)",
                          "unités : celles déclarées par IfcSIUnit ; vérifier l'unité de longueur avant tout rapprochement",
                          "IFC-XML et IFC compressé non pris en charge"]}
    if len(elements) > 3000:
        result["limites"].append(f"{len(elements) - 3000} éléments non détaillés (liste tronquée à 3000)")
    out_path = work / "controles" / f"ifc_{a.doc_id}.json"
    save_json(out_path, result)
    summary = {"statut": "ok" if not errors else "partiel", "outil": "ifc_probe", "fichier_resultat": str(out_path),
               **{k: result[k] for k in ("schema", "unites_si_declarees", "nb_entites", "niveaux",
                                         "elements_par_type", "elements_sans_quantite", "elements_sans_nom",
                                         "elements_sans_niveau", "sommes_quantites_par_type", "limites")}}
    journal(work, "ifc_probe", summary["statut"], {"fichier": str(path), "nb_entites": len(ents)})
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
