#!/usr/bin/env python3
"""Vérifie les livrables du scénario A (tests/test_e2e_simule.mjs) contre les situations attendues.

Usage : python3 tests/verifier_e2e.py <répertoire livrables_audit>
"""
import csv
import json
import re
import sys
from pathlib import Path

out = Path(sys.argv[1])
w = out / "_travail"
reg = json.loads((w / "registre.json").read_text(encoding="utf-8"))
idx = {f["finding_id"]: f for f in reg["constats"]}
remap = reg["correspondance_ids"]
echecs = []


def c(fid):
    return idx[remap.get(fid, fid)]


def ok(cond, msg):
    print(f"  {'✔' if cond else '✘'} {msg}")
    if not cond:
        echecs.append(msg)


rapport = (out / "rapport_audit_dossier_btp.md").read_text(encoding="utf-8")
questions = (out / "questions_a_arbitrer.md").read_text(encoding="utf-8")
risques = (out / "risques_et_interfaces.md").read_text(encoding="utf-8")


def section(nom):
    m = re.search(rf"<!-- section:{nom} -->(.*?)<!-- /section:{nom} -->", rapport, re.S)
    return m.group(1) if m else ""


etablis, desaccords = section("etablis"), section("desaccords")

print("  — situations du cahier des charges")
f = c("ECO-001")
ok(f["status"] == "corrobore" and f["evidence_level"] == "prouve_par_outil",
   "S2 erreur arithmétique : ECO-001 corroboré, prouvé par contrôle déterministe")
f = c("MET-001")
ok(remap.get("ENV-001") == "MET-001" and remap.get("ECO-002") == "MET-001",
   "S5 doublons : ENV-001 (juge) et ECO-002 (même contrôle) fusionnés dans MET-001")
ok(f["status"] == "corrobore" and {"metres", "enveloppe", "economie"} <= set(f["origin_agents"]),
   "S1 écart de quantité : MET-001 corroboré, détecté par 3 agents")
a_traiter = json.loads((w / "echanges" / "r1" / "a_traiter.json").read_text(encoding="utf-8"))
ok(any(e.get("destinataire") == "economie" and "co-auteur" in e["motif"] for e in a_traiter["ecartees"])
   and not any(e["a"] == "economie" for e in f.get("echanges", [])),
   "la question adressée à un co-auteur du constat fusionné n'est pas routée (réponse non indépendante)")
ok("Questions internes non traitées" in questions and "co-auteur" in questions,
   "les questions non routées restent visibles dans questions_a_arbitrer.md")
f = c("CCT-002")
ok(f["finding_type"] == "question_ouverte" and "détail D12" in questions,
   "S3 information manquante : CCT-002 reste une question ouverte, posée dans questions_a_arbitrer.md")
f = c("ECO-003")
ok(f["status"] == "refute" and any(e["verdict"] == "refute" and e["independant"] for e in f.get("echanges", []))
   and any(v["verdict"] == "refute" for v in f.get("verifications", [])),
   "S4 constat réfutable : ECO-003 réfuté par un pair (indice B) puis par le vérificateur")
ok("ECO-003" in rapport.split("## 9.")[1] and "ECO-003" not in etablis, "ECO-003 listé parmi les réfutés, pas parmi les établis")
ok(c("CCT-001")["status"] == "corrobore" and c("SYN-001")["status"] == "corrobore",
   "S6 interface : CCT-001 et SYN-001 corroborés")
ok("OPC-001" in risques and "SYN-001" in risques, "S6 : interface et dépendance OPC présentes dans risques_et_interfaces.md")
f = c("ARC-001")
ok(f["status"] == "non_resolu" and (f.get("arbitrage") or {}).get("decision") == "desaccord_persistant",
   "S7 désaccord : ARC-001 non résolu après arbitrage (désaccord persistant)")
ok("#### ARC-001" in desaccords and "ARC-001" not in etablis, "S7 : le désaccord est visible dans le rapport, hors des constats établis")
ok("épaisseur de la dalle" in questions.lower(), "S7 : la question d'arbitrage est transmise à la MOE")
f = c("CCT-003")
ok(remap.get("ENV-002") == "CCT-003" and f["status"] == "corrobore",
   "S8 consigne adressée à une IA : signalée par 2 agents, fusionnée, corroborée")
f = c("STR-001")
ok(f["status"] == "non_resolu" and f["finding_type"] == "question_ouverte",
   "preuve jugée insuffisante : STR-001 requalifié en question ouverte, non résolu")
f = c("CMP-101")
ok(f.get("verifications") and f["status"] == "corrobore", "complétude : CMP-101 ajouté puis vérifié")
for fid in ("ARC-002", "BIM-001", "REF-001", "CVC-001"):
    ok(c(fid)["status"] == "a_verifier", f"{fid} reste « à vérifier » (un seul agent, non sélectionné)")

print("  — intégrité des livrables")
attendus = ["rapport_audit_dossier_btp.md", "registre_anomalies.csv", "registre_anomalies.xlsx",
            "rapprochement_economique.csv", "questions_a_arbitrer.md", "risques_et_interfaces.md",
            "manifeste_documentaire.csv", "journal_controles.md"]
ok(all((out / x).exists() and (out / x).stat().st_size > 0 for x in attendus), "tous les livrables existent et sont non vides")
with open(out / "registre_anomalies.csv", encoding="utf-8-sig", newline="") as fh:
    rows = list(csv.DictReader(fh, delimiter=";"))
ok(len(rows) == len(reg["constats"]), f"registre CSV : {len(rows)} lignes = {len(reg['constats'])} constats")
with open(out / "rapprochement_economique.csv", encoding="utf-8-sig", newline="") as fh:
    rap = {r["controle_id"]: r for r in csv.DictReader(fh, delimiter=";")}
r = rap.get("RAPP-D007-D006-002", {})
ok(r.get("statut") == "ecart" and "MET-001" in r.get("constats_lies", "") and r.get("ecart_abs") == "27,500",
   "rapprochement : écart 27,5 m² relié à MET-001 (virgule décimale)")
ok(rap.get("DPGF-D005-F1-L8-ARITH", {}).get("ecart_montant") == "-360,00", "rapprochement : contrôle arithmétique -360,00 €")
with open(out / "manifeste_documentaire.csv", encoding="utf-8-sig", newline="") as fh:
    man = {r["doc_id"]: r for r in csv.DictReader(fh, delimiter=";")}
ok(man["D011"]["statut_exploitation"] == "doublon" and "AUCUN" not in man["D002"]["examine_par"], "manifeste : doublon signalé, couverture renseignée")
flags = [x["finding_id"] for x in reg["constats"] if "citation_non_retrouvee" in x.get("quality_flags", [])]
ok(not flags, f"toutes les citations sont retrouvées mot pour mot dans les pièces ({flags or 'aucune anomalie'})")
q = json.loads((w / "controle_qualite.json").read_text(encoding="utf-8"))
ok(q["verdict"] != "non_conforme", f"porte qualité finale : {q['verdict']}")
ok(all(x["resultat"] == "ok" for x in q["controles"] if x["controle"] in ("Q04", "Q05")),
   "porte qualité : Q04 (établis) et Q05 (synthèse) conformes après correction")
journal = (out / "journal_controles.md").read_text(encoding="utf-8")
for outil in ("preflight", "inventaire", "dpgf_check", "rapprochement", "ifc_probe", "registre.build",
              "registre.transmissions", "registre.selection", "livrables", "controle_qualite"):
    ok(f"| {outil} |" in journal, f"journal : {outil} tracé")
for titre in ("1. Synthèse exécutive", "2. Périmètre", "3. Limites", "4. Constats établis", "6. Désaccords",
              "7. Risques économiques", "8. Incohérences et interfaces", "10. Recommandations"):
    ok(f"## {titre}" in rapport, f"rapport : rubrique « {titre} »")
for fid in re.findall(r"^#### ([A-Z]{2,5}-\d{3})", etablis, re.M):
    if idx[fid]["status"] != "corrobore":
        echecs.append(f"{fid} présenté comme établi")
ok(True, "contrôle indépendant de la section des constats établis effectué")

if echecs:
    print(f"\n  {len(echecs)} échec(s)")
    sys.exit(1)
print("  scénario A conforme")
