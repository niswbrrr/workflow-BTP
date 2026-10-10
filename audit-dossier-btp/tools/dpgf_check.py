#!/usr/bin/env python3
"""Contrôle déterministe d'une pièce économique quantitative (DPGF, DQE, BPU chiffré, métré).

Usage :
  python dpgf_check.py --fichier <xlsx|csv> --travail <_travail> [--doc-id D004]
         [--feuille NOM] [--col-ref N --col-designation N --col-unite N --col-quantite N
          --col-pu N --col-montant N] [--tva 20]

Contrôles (chacun reçoit un identifiant stable « DPGF-<doc>-<f>-L<ligne>-<TYPE> ») :
  ARITH            quantité × PU ≠ montant (écart > 0,01 € et > 0,05 € => erreur ; sinon arrondi)
  SOUS_TOTAL       sous-total déclaré ≠ somme recalculée
  TOTAL            total déclaré ≠ somme des articles
  TVA / TTC        TVA ou TTC incohérents avec le total HT
  QTE_MANQUANTE    article sans quantité (hors forfait / PM)
  PU_MANQUANT      article sans prix unitaire dans une pièce chiffrée
  MONTANT_MANQUANT article avec quantité et PU mais sans montant
  QTE_NULLE / VALEUR_NEGATIVE
  UNITE_INCONNUE   unité non reconnue
  UNITE_A_EXAMINER indice faible : unité peu cohérente avec le libellé
  DOUBLON          même libellé et même unité sur plusieurs lignes (à examiner, peut être légitime)
Les gravités produites sont INDICATIVES : la qualification finale revient à l'agent économie.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from btp_common import (cell, detect_header, journal, norm_text, norm_unit,  # noqa: E402
                        parse_number, print_summary, read_table, save_json)

TOTAL_RE = re.compile(r"^\s*(sous[- ]?total|total|montant total|report|a reporter|tva|t\.v\.a|montant tva)", re.I)
SECTION_CODE_RE = re.compile(r"\b(\d+(?:\.\d+)*)\b")
SURFACE_WORDS = {"enduit", "peinture", "carrelage", "chape", "doublage", "cloison", "plafond", "dallage",
                 "etancheite", "isolation", "isolant", "faience", "revetement", "parquet", "bardage", "couverture",
                 "ravalement", "enduits", "badigeon", "sol", "murs"}
LINEAR_WORDS = {"plinthe", "plinthes", "garde-corps", "gouttiere", "cheneau", "couvertine", "bande", "joint",
                "linteau", "corniche", "rive", "faitage", "descente", "fourreau", "goulotte", "chemin"}


def load_lines(path, sheet=None, overrides=None):
    """Lit un tableau quantitatif et renvoie la liste des feuilles normalisées."""
    sheets, missing = read_table(path)
    out = []
    for s_idx, sh in enumerate(sheets, start=1):
        if sheet and sh["name"] != sheet:
            continue
        rows = sh["rows"]
        h_idx, cols = detect_header(rows, overrides=overrides)
        entry = {"index": s_idx, "nom": sh["name"], "entete_ligne": rows[h_idx][0] if h_idx is not None else None,
                 "colonnes": cols, "lignes": []}
        if h_idx is None or "designation" not in cols:
            entry["erreur"] = "en-tête non détecté (colonnes Désignation/Unité/Quantité/PU/Montant) : préciser --col-*"
            entry["apercu"] = [{"ligne": r, "cellules": [str(c)[:40] for c in cells[:8]]} for r, cells in rows[:10]]
            out.append(entry)
            continue
        for rnum, cells in rows[h_idx + 1:]:
            des = str(cell(cells, cols.get("designation"))).strip()
            ref = str(cell(cells, cols.get("ref"))).strip() if "ref" in cols else ""
            unit_raw = str(cell(cells, cols.get("unite"))).strip() if "unite" in cols else ""
            qty = parse_number(cell(cells, cols.get("quantite"))) if "quantite" in cols else None
            pu = parse_number(cell(cells, cols.get("pu"))) if "pu" in cols else None
            mt = parse_number(cell(cells, cols.get("montant"))) if "montant" in cols else None
            if not des and not ref and qty is None and pu is None and mt is None:
                continue
            label = des or ref
            if TOTAL_RE.match(norm_text(label)):
                kind = "total"
            elif qty is None and pu is None and mt is None and not unit_raw:
                kind = "titre"
            else:
                kind = "article"
            entry["lignes"].append({"ligne": rnum, "ref": ref, "designation": des, "unite": unit_raw,
                                    "unite_norm": norm_unit(unit_raw) if unit_raw else None,
                                    "quantite": qty, "pu": pu, "montant": mt, "type": kind})
        out.append(entry)
    return out, missing


def norm_code(ref):
    """« 02.1 » -> « 2.1 » : supprime les zéros non significatifs de chaque segment."""
    parts = [p.lstrip("0") or "0" for p in str(ref or "").strip().strip(".").split(".") if p != ""]
    return ".".join(parts)


def cid(doc, s_idx, line, kind):
    return f"DPGF-{doc}-F{s_idx}-L{line}-{kind}"


def money(x):
    return None if x is None else round(x, 2)


def check_sheet(sh, doc, tva_default):
    controls = []
    arts = [l for l in sh["lignes"] if l["type"] == "article"]
    priced = [a for a in arts if a["pu"] is not None]
    if not arts:
        etat = "vide"
    elif not priced:
        etat = "cadre_vierge"
    elif len(priced) >= 0.5 * len(arts):
        etat = "chiffree"
    else:
        etat = "partiellement_chiffree"
    total_calc = sum(a["montant"] or 0 for a in arts)

    def add(line, kind, gravite, commentaire, **vals):
        controls.append({"controle_id": cid(doc, sh["index"], line["ligne"], kind), "type": kind,
                         "feuille": sh["nom"], "ligne": line["ligne"], "ref": line.get("ref"),
                         "designation": line.get("designation"), "gravite_indicative": gravite,
                         "commentaire": commentaire, **vals})

    for a in arts:
        u = a["unite_norm"]
        forfait = u in ("ens", "pm")
        q, p, m = a["quantite"], a["pu"], a["montant"]
        for name, v in (("quantite", q), ("pu", p), ("montant", m)):
            if v is not None and v < 0:
                add(a, "VALEUR_NEGATIVE", "moderee", f"{name} négatif", valeur=v)
        if q is not None and p is not None and m is not None:
            exp = q * p
            diff = m - exp
            if abs(diff) > 0.01 + 1e-9 * abs(exp):
                kind = "ARITH" if abs(diff) > 0.05 else "ARRONDI"
                grav = "mineure" if kind == "ARRONDI" else (
                    "majeure" if total_calc and abs(diff) >= 0.01 * abs(total_calc) else "moderee")
                add(a, kind, grav, "quantité × PU ≠ montant déclaré",
                    formule="quantite * pu", quantite=q, pu=p, montant_declare=money(m),
                    montant_recalcule=money(exp), ecart=money(diff))
        elif q is not None and p is not None and m is None and etat != "cadre_vierge":
            add(a, "MONTANT_MANQUANT", "moderee", "quantité et PU présents, montant absent",
                quantite=q, pu=p, montant_recalcule=money(q * p))
        if q is None and not forfait and a["unite"]:
            add(a, "QTE_MANQUANTE", "moderee", "article quantifiable sans quantité", unite=a["unite"])
        if q == 0:
            add(a, "QTE_NULLE", "mineure", "quantité nulle : ligne sans objet ou oubli ?")
        if etat in ("chiffree", "partiellement_chiffree") and p is None and m is None and not (u == "pm"):
            add(a, "PU_MANQUANT", "moderee", "pièce chiffrée mais article sans PU ni montant")
        if a["unite"] and u and u.startswith("?"):
            add(a, "UNITE_INCONNUE", "mineure", f"unité non reconnue : « {a['unite']} »")
        words = set(norm_text(a["designation"]).split())
        if u in ("ml", "u") and words & SURFACE_WORDS and not words & LINEAR_WORDS:
            add(a, "UNITE_A_EXAMINER", "mineure", "indice faible : libellé évoquant une surface, unité "
                f"« {a['unite']} »", unite=a["unite"])

    groups = defaultdict(list)
    for a in arts:
        groups[(norm_text(a["designation"]), a["unite_norm"])].append(a)
    for (des, _), items in groups.items():
        if des and len(items) > 1:
            first = items[0]
            add(first, "DOUBLON", "mineure", "même libellé et même unité sur plusieurs lignes "
                "(peut être légitime si sections différentes)", lignes=[i["ligne"] for i in items],
                refs=[i["ref"] for i in items])

    acc = 0.0
    ht_declared = None
    tva_amount = None
    for line in sh["lignes"]:
        if line["type"] == "article":
            acc += line["montant"] or 0
            continue
        if line["type"] != "total" or line["montant"] is None:
            continue
        label = norm_text(line["designation"] or line["ref"])
        declared = line["montant"]
        if label.startswith("tva") or label.startswith("t.v.a") or "montant tva" in label:
            rate_m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", line["designation"] or "")
            rate = parse_number(rate_m.group(1)) if rate_m else tva_default
            base = ht_declared if ht_declared is not None else total_calc
            exp = base * rate / 100.0
            tva_amount = declared
            if abs(declared - exp) > 0.01:
                add(line, "TVA", "moderee", f"TVA {rate} % incohérente avec la base HT",
                    base_ht=money(base), taux=rate, montant_declare=money(declared), montant_recalcule=money(exp),
                    ecart=money(declared - exp))
            continue
        if "ttc" in label:
            base = ht_declared if ht_declared is not None else total_calc
            if tva_amount is not None:
                exp = base + tva_amount
                if abs(declared - exp) > 0.01:
                    add(line, "TTC", "moderee", "TTC ≠ HT + TVA", montant_declare=money(declared),
                        montant_recalcule=money(exp), ecart=money(declared - exp))
            continue
        if label.startswith("sous"):
            code_m = SECTION_CODE_RE.search(line["designation"] or "")
            matched = []
            if code_m:
                code = norm_code(code_m.group(1))
                matched = [a for a in arts if norm_code(a["ref"]) == code or norm_code(a["ref"]).startswith(code + ".")]
            if matched:
                exp = sum(a["montant"] or 0 for a in matched)
                base_desc = f"articles dont la référence commence par {code}"
            else:
                exp = acc
                base_desc = "articles depuis le sous-total précédent"
            acc = 0.0
            if abs(declared - exp) > 0.01:
                add(line, "SOUS_TOTAL", "majeure" if abs(declared - exp) >= 0.01 * max(abs(total_calc), 1) else "moderee",
                    "sous-total déclaré ≠ somme recalculée", base=base_desc, montant_declare=money(declared),
                    montant_recalcule=money(exp), ecart=money(declared - exp))
        else:
            ht_declared = declared
            if abs(declared - total_calc) > 0.01:
                add(line, "TOTAL", "majeure", "total déclaré ≠ somme des articles", montant_declare=money(declared),
                    montant_recalcule=money(total_calc), ecart=money(declared - total_calc))
    return etat, total_calc, controls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fichier", required=True)
    ap.add_argument("--travail", required=True)
    ap.add_argument("--doc-id", default=None)
    ap.add_argument("--feuille", default=None)
    ap.add_argument("--tva", type=float, default=20.0)
    for k in ("ref", "designation", "unite", "quantite", "pu", "montant"):
        ap.add_argument(f"--col-{k}", type=int, default=None, help="index de colonne (0 = A)")
    a = ap.parse_args()
    path = Path(a.fichier).expanduser().resolve()
    work = Path(a.travail).expanduser().resolve()
    doc = a.doc_id or re.sub(r"\W+", "_", path.stem)[:20]
    overrides = {k: getattr(a, f"col_{k}") for k in ("ref", "designation", "unite", "quantite", "pu", "montant")}
    overrides = {k: v for k, v in overrides.items() if v is not None} or None

    try:
        sheets, missing = load_lines(path, a.feuille, overrides)
    except Exception as exc:
        print_summary({"statut": "echec", "outil": "dpgf_check", "erreur": f"{type(exc).__name__}: {exc}"})
        journal(work, "dpgf_check", "echec", {"fichier": str(path), "erreur": str(exc)})
        return 0

    result = {"outil": "dpgf_check", "fichier": str(path), "doc_id": doc, "feuilles": [],
              "formules_sans_cache": missing}
    all_controls = []
    lines_csv = work / "controles" / f"dpgf_{doc}_lignes.csv"
    lines_csv.parent.mkdir(parents=True, exist_ok=True)
    with lines_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["doc_id", "feuille", "ligne", "type", "ref", "designation", "unite", "unite_norm",
                    "quantite", "pu", "montant"])
        for sh in sheets:
            info = {"nom": sh["nom"], "index": sh["index"], "entete_ligne": sh.get("entete_ligne"),
                    "colonnes": sh.get("colonnes")}
            if "erreur" in sh:
                info.update(erreur=sh["erreur"], apercu=sh.get("apercu"))
                result["feuilles"].append(info)
                continue
            etat, total, controls = check_sheet(sh, doc, a.tva)
            info.update(etat_chiffrage=etat, nb_articles=sum(1 for l in sh["lignes"] if l["type"] == "article"),
                        total_articles_recalcule=round(total, 2), nb_controles=len(controls))
            result["feuilles"].append(info)
            all_controls.extend(controls)
            for l in sh["lignes"]:
                w.writerow([doc, sh["nom"], l["ligne"], l["type"], l["ref"], l["designation"], l["unite"],
                            l["unite_norm"] or "", l["quantite"] if l["quantite"] is not None else "",
                            l["pu"] if l["pu"] is not None else "", l["montant"] if l["montant"] is not None else ""])
    result["controles"] = all_controls
    result["lignes_normalisees"] = str(lines_csv)
    out_path = work / "controles" / f"dpgf_{doc}.json"
    save_json(out_path, result)

    by_type = defaultdict(int)
    for c in all_controls:
        by_type[c["type"]] += 1
    important = [c for c in all_controls if c["type"] in ("ARITH", "TOTAL", "SOUS_TOTAL", "TVA", "TTC",
                                                          "MONTANT_MANQUANT", "VALEUR_NEGATIVE")]
    summary = {"statut": "ok" if all("erreur" not in f for f in result["feuilles"]) else "partiel",
               "outil": "dpgf_check", "doc_id": doc, "fichier_resultat": str(out_path),
               "feuilles": [{k: f.get(k) for k in ("nom", "etat_chiffrage", "nb_articles",
                                                     "total_articles_recalcule", "nb_controles", "colonnes",
                                                     "erreur")} for f in result["feuilles"]],
               "controles_par_type": dict(by_type),
               "controles_principaux": [{k: c.get(k) for k in ("controle_id", "type", "ligne", "ref", "designation",
                                                                 "montant_declare", "montant_recalcule", "ecart")}
                                        for c in important[:30]]}
    journal(work, "dpgf_check", summary["statut"], {"fichier": str(path), "doc_id": doc,
                                                    "controles_par_type": dict(by_type)})
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
