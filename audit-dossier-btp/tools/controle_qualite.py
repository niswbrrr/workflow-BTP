#!/usr/bin/env python3
"""Phase 11 — porte qualité déterministe sur les livrables.

Usage :
  python controle_qualite.py --travail <_travail>

Contrôles :
  Q01 présence et non-vacuité des livrables attendus
  Q02 registre CSV relisible, identifiants uniques, cohérent avec registre.json
  Q03 sources : documents existants, pages dans les bornes
  Q04 section « constats établis » du rapport : uniquement des constats corroborés
  Q05 synthèse rédigée : identifiants existants, aucun constat réfuté présenté comme message clé
  Q06 calculs : aucun constat corroboré avec calcul faux / contrôle introuvable / incohérent
  Q07 rapprochement CSV : écarts recalculés
  Q08 impacts économiques chiffrés accompagnés d'une base de calcul
  Q09 références normatives citées par les agents absentes du dossier et non sourcées (risque d'invention)
  Q10 documents jamais examinés et agents en échec mentionnés dans les limites du rapport
  Q11 doublons résiduels évidents (même titre normalisé et même lot)
  Q12 citations non retrouvées dans les pièces
Le résultat est ajouté au journal et en fin de rapport. Un échec n'efface rien : il est signalé.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from btp_common import journal, load_json, norm_text, parse_number, print_summary, save_json  # noqa: E402

DELIVERABLES = ["rapport_audit_dossier_btp.md", "registre_anomalies.csv", "rapprochement_economique.csv",
                "questions_a_arbitrer.md", "risques_et_interfaces.md", "manifeste_documentaire.csv",
                "journal_controles.md"]
NORM_RE = re.compile(r"\b(?:NF\s+)?DTU\s*\d{1,2}(?:\.\d{1,2})?|\bNF\s+EN\s+(?:ISO\s+)?\d{2,5}(?:-\d+)*|"
                     r"\bNF\s+[A-Z]\s?\d{2}-\d{3}|\bEurocode\s*\d{1,2}\b", re.I)


def norm_ref(s):
    s = re.sub(r"\s+", " ", s.upper().replace("NF DTU", "DTU")).strip()
    return s


def section(text, name):
    m = re.search(rf"<!-- section:{name} -->(.*?)<!-- /section:{name} -->", text, re.S)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--travail", required=True)
    a = ap.parse_args()
    work = Path(a.travail).resolve()
    out = work.parent
    errors, warnings, done = [], [], []

    def check(code, label, ok, detail=None):
        done.append({"controle": code, "libelle": label, "resultat": "ok" if ok else "ko",
                     **({"detail": detail} if detail else {})})

    reg = load_json(work / "registre.json")
    man = load_json(work / "manifeste.json", {"documents": [], "normes_citees": []})
    etat = load_json(work / "etat_execution.json", {}) or {}
    synth = load_json(work / "synthese.json", None)
    if reg is None:
        print_summary({"statut": "echec", "outil": "controle_qualite", "erreur": "registre.json absent"})
        return 0
    findings = reg["constats"]
    index = {f["finding_id"]: f for f in findings}
    docs = {d["doc_id"]: d for d in man.get("documents", [])}

    # Q01
    missing = [f for f in DELIVERABLES if not (out / f).exists() or (out / f).stat().st_size == 0]
    for f in missing:
        errors.append(f"Q01 livrable absent ou vide : {f}")
    check("Q01", "présence des livrables", not missing, missing or None)

    # Q02
    q2 = []
    try:
        with open(out / "registre_anomalies.csv", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter=";"))
        ids = [r["finding_id"] for r in rows]
        dup = [i for i, n in Counter(ids).items() if n > 1]
        if dup:
            q2.append(f"identifiants en double dans le CSV : {dup}")
        if set(ids) != set(index):
            q2.append(f"CSV ({len(ids)} lignes) incohérent avec registre.json ({len(index)} constats)")
    except Exception as exc:
        q2.append(f"CSV illisible : {exc}")
    errors += [f"Q02 {x}" for x in q2]
    check("Q02", "registre CSV cohérent", not q2, q2 or None)

    # Q03
    q3 = []
    for f in findings:
        for s in f.get("sources", []):
            did = s.get("doc_id")
            if did != "EXT" and did not in docs:
                q3.append(f"{f['finding_id']} cite un document inexistant {did}")
            elif s.get("verification") == "page_hors_document":
                q3.append(f"{f['finding_id']} cite une page hors document ({did} p.PDF {s.get('page_pdf')})")
            elif did == "EXT" and not s.get("url"):
                q3.append(f"{f['finding_id']} cite une source externe sans référence")
        if not f.get("sources") and f["status"] == "corrobore":
            q3.append(f"{f['finding_id']} corroboré sans aucune source")
    errors += [f"Q03 {x}" for x in q3]
    check("Q03", "intégrité des sources", not q3, q3[:20] or None)

    # Q04
    report = (out / "rapport_audit_dossier_btp.md").read_text(encoding="utf-8") if (out / "rapport_audit_dossier_btp.md").exists() else ""
    sec = section(report, "etablis")
    q4 = []
    if sec is None:
        q4.append("section des constats établis introuvable dans le rapport")
    else:
        listed = set(re.findall(r"^#### ([A-Z]{2,5}-\d{3}(?:-[a-z0-9]+)?) ", sec, re.M)) | \
            set(re.findall(r"^\| ([A-Z]{2,5}-\d{3}(?:-[a-z0-9]+)?) \|", sec, re.M))
        for fid in sorted(listed):
            f = index.get(fid)
            if f is None:
                q4.append(f"{fid} présenté comme établi mais absent du registre")
            elif f["status"] != "corrobore":
                q4.append(f"{fid} présenté comme établi alors que son statut est « {f['status']} »")
    errors += [f"Q04 {x}" for x in q4]
    check("Q04", "aucun constat non corroboré présenté comme établi", not q4, q4 or None)

    # Q05
    q5e, q5w = [], []
    if synth:
        for block in synth.get("messages_cles", []) + synth.get("decisions_prioritaires", []):
            for fid in block.get("constats", []):
                f = index.get(fid) or index.get(reg.get("correspondance_ids", {}).get(fid, ""))
                if f is None:
                    q5e.append(f"synthèse : identifiant inconnu {fid}")
                elif f["status"] == "refute":
                    q5e.append(f"synthèse : {fid} est réfuté mais cité comme message clé ou décision")
                elif f["status"] in ("conteste", "non_resolu", "a_verifier"):
                    q5w.append(f"synthèse : {fid} cité avec le statut « {f['status']} » (étiqueté dans le rapport)")
    else:
        q5w.append("synthèse rédigée absente")
    errors += [f"Q05 {x}" for x in q5e]
    warnings += [f"Q05 {x}" for x in q5w]
    check("Q05", "synthèse cohérente avec les statuts", not q5e, (q5e + q5w) or None)

    # Q06
    q6 = [f"{f['finding_id']} : {fl}" for f in findings if f["status"] == "corrobore"
          for fl in f.get("quality_flags", []) if fl in ("calcul_faux", "controle_introuvable",
                                                          "calcul_incoherent_avec_outil")]
    q6w = [f"{f['finding_id']} : {fl}" for f in findings if f["status"] != "corrobore"
           for fl in f.get("quality_flags", []) if fl in ("calcul_faux", "controle_introuvable",
                                                           "calcul_incoherent_avec_outil")]
    errors += [f"Q06 {x}" for x in q6]
    warnings += [f"Q06 {x}" for x in q6w]
    check("Q06", "calculs des constats corroborés vérifiés", not q6, (q6 + q6w) or None)

    # Q07
    q7 = []
    try:
        with open(out / "rapprochement_economique.csv", encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                qa, qb, ea = parse_number(r.get("quantite_a")), parse_number(r.get("quantite_b")), parse_number(r.get("ecart_abs"))
                if r.get("type_controle") == "rapprochement_quantites" and None not in (qa, qb, ea):
                    if abs((qa - qb) - ea) > 0.002:
                        q7.append(f"{r['controle_id']} : écart {ea} ≠ {qa} − {qb}")
    except Exception as exc:
        q7.append(f"rapprochement illisible : {exc}")
    errors += [f"Q07 {x}" for x in q7]
    check("Q07", "écarts du rapprochement recalculés", not q7, q7 or None)

    # Q08
    q8 = []
    for f in findings:
        e = f.get("economic_impact") or {}
        if e.get("quantifie") and (e.get("montant_ht") is None or not (e.get("base") or "").strip()):
            q8.append(f"{f['finding_id']} : impact déclaré chiffré sans montant ou sans base de calcul")
    errors += [f"Q08 {x}" for x in q8]
    check("Q08", "impacts chiffrés justifiés", not q8, q8 or None)

    # Q09
    in_dossier = {norm_ref(n["reference"]) for n in man.get("normes_citees", [])}
    q9 = []
    for f in findings:
        has_ext = any(s.get("doc_id") == "EXT" and s.get("url") for s in f.get("sources", []))
        text = " ".join([f.get("claim", ""), f.get("recommended_action", ""), f.get("severity_rationale", ""),
                         " ".join(e["fait"] for e in f.get("evidence", []))])
        for m in NORM_RE.finditer(text):
            ref = norm_ref(m.group(0))
            if not any(ref in x or x in ref for x in in_dossier) and not has_ext:
                q9.append(f"{f['finding_id']} mentionne « {m.group(0)} » : absente des pièces et sans source externe")
    warnings += [f"Q09 {x}" for x in q9]
    check("Q09", "références normatives traçables", not q9, q9 or None)

    # Q10
    lim = section(report, "limites") or ""
    q10 = []
    for d in reg.get("couverture", {}).get("documents_jamais_examines", []):
        if d["doc_id"] not in lim:
            q10.append(f"{d['doc_id']} jamais examiné mais absent des limites du rapport")
    for ag in etat.get("agents", []):
        if ag.get("statut") in ("echec", "vide", "abandon") and ag.get("label", "") not in lim:
            q10.append(f"agent {ag.get('label')} en {ag.get('statut')} non mentionné dans les limites")
    errors += [f"Q10 {x}" for x in q10]
    check("Q10", "limites complètes", not q10, q10 or None)

    # Q11
    keys = Counter((norm_text(f["title"]), norm_text(f.get("lot", ""))) for f in findings if f["status"] != "refute")
    q11 = [f"titre en double : {k[0]} (lot {k[1]})" for k, n in keys.items() if n > 1]
    warnings += [f"Q11 {x}" for x in q11]
    check("Q11", "pas de doublon résiduel évident", not q11, q11 or None)

    # Q12
    q12 = [f["finding_id"] for f in findings if "citation_non_retrouvee" in f.get("quality_flags", [])]
    if q12:
        warnings.append(f"Q12 citations non retrouvées dans les pièces (confiance abaissée) : {', '.join(q12)}")
    check("Q12", "citations retrouvées", not q12, q12 or None)

    verdict = "non_conforme" if errors else ("conforme_avec_reserves" if warnings else "conforme")
    res = {"outil": "controle_qualite", "verdict": verdict, "erreurs": errors, "avertissements": warnings,
           "controles": done}
    save_json(work / "controle_qualite.json", res)
    block = ["", "## Contrôle qualité automatique des livrables", "", f"**Verdict** : {verdict}", ""]
    block += [f"- {c['controle']} {c['libelle']} : {c['resultat']}" for c in done]
    if errors:
        block += ["", "**Erreurs**", ""] + [f"- {e}" for e in errors]
    if warnings:
        block += ["", "**Avertissements**", ""] + [f"- {w}" for w in warnings]
    marker = "<!-- controle_qualite -->"
    for name in ("rapport_audit_dossier_btp.md", "journal_controles.md"):
        p = out / name
        if p.exists():
            txt = p.read_text(encoding="utf-8").split(marker)[0].rstrip("\n")
            p.write_text(txt + "\n\n" + marker + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    journal(work, "controle_qualite", verdict, {"erreurs": len(errors), "avertissements": len(warnings)})
    print_summary({"statut": "ok", "outil": "controle_qualite", "verdict": verdict, "erreurs": errors[:30],
                   "avertissements": warnings[:30]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
