#!/usr/bin/env python3
"""Rapprochement déterministe des quantités entre deux pièces quantitatives.

Usage :
  python rapprochement.py --a <fichier> --b <fichier> --travail <_travail>
         [--doc-a D005 --doc-b D004] [--nom-a metre --nom-b dpgf] [--seuil 0.02]
         [--feuille-a NOM] [--feuille-b NOM]

Appariement :
  1. référence identique (après normalisation) ;
  2. sinon libellé proche (indice de Jaccard sur les mots significatifs ≥ 0,5),
     appariement glouton du meilleur score ; < 0,7 => « a_confirmer ».
Statuts : concordant | ecart | unite_differente | a_confirmer | absent_de_B | absent_de_A.
Aucun écart n'est calculé quand une quantité manque ou que les unités diffèrent.
Valorisation indicative de l'écart au PU de la pièce B uniquement si ce PU existe.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from btp_common import jaccard, journal, print_summary, save_json, tokens  # noqa: E402
from dpgf_check import load_lines  # noqa: E402


def norm_ref(r: str) -> str:
    return re.sub(r"[\s.]+$", "", re.sub(r"\s+", "", (r or "").lower()))


def articles(path, sheet):
    sheets, _ = load_lines(path, sheet)
    out = []
    errors = []
    for sh in sheets:
        if "erreur" in sh:
            errors.append(f"{sh['nom']}: {sh['erreur']}")
            continue
        for l in sh["lignes"]:
            if l["type"] == "article":
                out.append({**l, "feuille": sh["nom"], "tok": tokens(l["designation"])})
    return out, errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--travail", required=True)
    ap.add_argument("--doc-a", default="A")
    ap.add_argument("--doc-b", default="B")
    ap.add_argument("--nom-a", default="piece_A")
    ap.add_argument("--nom-b", default="piece_B")
    ap.add_argument("--feuille-a", default=None)
    ap.add_argument("--feuille-b", default=None)
    ap.add_argument("--seuil", type=float, default=0.02, help="écart relatif toléré (0,02 = 2 %)")
    a = ap.parse_args()
    work = Path(a.travail).expanduser().resolve()

    try:
        A, err_a = articles(Path(a.a).expanduser(), a.feuille_a)
        B, err_b = articles(Path(a.b).expanduser(), a.feuille_b)
    except Exception as exc:
        print_summary({"statut": "echec", "outil": "rapprochement", "erreur": f"{type(exc).__name__}: {exc}"})
        journal(work, "rapprochement", "echec", {"erreur": str(exc)})
        return 0

    pairs = []
    used_b = set()
    # 1. références identiques
    idx_b = {}
    for j, b in enumerate(B):
        if b["ref"]:
            idx_b.setdefault(norm_ref(b["ref"]), j)
    rest_a = []
    for i, x in enumerate(A):
        j = idx_b.get(norm_ref(x["ref"])) if x["ref"] else None
        if j is not None and j not in used_b:
            used_b.add(j)
            pairs.append((i, j, "reference", 1.0))
        else:
            rest_a.append(i)
    # 2. libellés proches
    cands = []
    for i in rest_a:
        for j, y in enumerate(B):
            if j in used_b:
                continue
            s = jaccard(A[i]["tok"], y["tok"])
            if s >= 0.5:
                cands.append((s, i, j))
    cands.sort(key=lambda t: (-t[0], t[1], t[2]))
    used_a = set()
    for s, i, j in cands:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        pairs.append((i, j, "libelle", round(s, 2)))
    matched_a = {p[0] for p in pairs}

    lines = []
    n = 0
    for i, j, how, score in sorted(pairs, key=lambda p: (A[p[0]]["feuille"], A[p[0]]["ligne"])):
        x, y = A[i], B[j]
        n += 1
        rec = {"controle_id": f"RAPP-{a.doc_a}-{a.doc_b}-{n:03d}", "appariement": how, "score_libelle": score,
               "doc_a": a.doc_a, "feuille_a": x["feuille"], "ligne_a": x["ligne"], "ref_a": x["ref"],
               "designation_a": x["designation"], "unite_a": x["unite"], "quantite_a": x["quantite"],
               "doc_b": a.doc_b, "feuille_b": y["feuille"], "ligne_b": y["ligne"], "ref_b": y["ref"],
               "designation_b": y["designation"], "unite_b": y["unite"], "quantite_b": y["quantite"],
               "pu_b": y["pu"]}
        if x["unite_norm"] and y["unite_norm"] and x["unite_norm"] != y["unite_norm"]:
            rec["statut"] = "unite_differente"
            rec["commentaire"] = "unités différentes : aucun écart calculé"
        elif x["quantite"] is None or y["quantite"] is None:
            rec["statut"] = "donnee_manquante"
            rec["commentaire"] = "quantité absente d'un côté : écart non calculable"
        else:
            d = x["quantite"] - y["quantite"]
            base = max(abs(x["quantite"]), abs(y["quantite"]), 1e-9)
            rec["ecart_abs"] = round(d, 3)
            rec["ecart_rel"] = round(d / base, 4)
            rec["formule"] = "quantite_a - quantite_b"
            rec["statut"] = "concordant" if abs(d) / base <= a.seuil else "ecart"
            if rec["statut"] == "ecart" and y["pu"] is not None:
                rec["valorisation_indicative_ht"] = round(d * y["pu"], 2)
                rec["base_valorisation"] = f"écart × PU de {a.nom_b} ({y['pu']})"
        if how == "libelle" and score < 0.7 and rec["statut"] in ("concordant", "ecart"):
            rec["statut_appariement"] = "a_confirmer"
        lines.append(rec)
    for i, x in enumerate(A):
        if i not in matched_a:
            n += 1
            lines.append({"controle_id": f"RAPP-{a.doc_a}-{a.doc_b}-{n:03d}", "statut": f"absent_de_{a.nom_b}",
                          "doc_a": a.doc_a, "feuille_a": x["feuille"], "ligne_a": x["ligne"], "ref_a": x["ref"],
                          "designation_a": x["designation"], "unite_a": x["unite"], "quantite_a": x["quantite"],
                          "commentaire": "aucune ligne correspondante trouvée (absence de correspondance ≠ omission "
                                         "prouvée : la prestation peut être regroupée ailleurs)"})
    for j, y in enumerate(B):
        if j not in used_b:
            n += 1
            lines.append({"controle_id": f"RAPP-{a.doc_a}-{a.doc_b}-{n:03d}", "statut": f"absent_de_{a.nom_a}",
                          "doc_b": a.doc_b, "feuille_b": y["feuille"], "ligne_b": y["ligne"], "ref_b": y["ref"],
                          "designation_b": y["designation"], "unite_b": y["unite"], "quantite_b": y["quantite"],
                          "commentaire": "aucune ligne correspondante trouvée"})

    out = {"outil": "rapprochement", "piece_a": {"doc_id": a.doc_a, "nom": a.nom_a, "fichier": str(a.a)},
           "piece_b": {"doc_id": a.doc_b, "nom": a.nom_b, "fichier": str(a.b)}, "seuil_relatif": a.seuil,
           "erreurs_lecture": err_a + err_b, "lignes": lines}
    out_path = work / "controles" / f"rapprochement_{a.doc_a}_{a.doc_b}.json"
    save_json(out_path, out)
    counts = Counter(l["statut"] for l in lines)
    ecarts = sorted([l for l in lines if l["statut"] == "ecart"], key=lambda l: -abs(l.get("ecart_rel", 0)))
    summary = {"statut": "ok" if not (err_a or err_b) else "partiel", "outil": "rapprochement",
               "fichier_resultat": str(out_path), "nb_articles_a": len(A), "nb_articles_b": len(B),
               "par_statut": dict(counts), "erreurs_lecture": err_a + err_b,
               "ecarts_principaux": [{k: l.get(k) for k in ("controle_id", "ref_a", "designation_a", "unite_a",
                                                            "quantite_a", "quantite_b", "ecart_rel",
                                                            "valorisation_indicative_ht")} for l in ecarts[:25]]}
    journal(work, "rapprochement", summary["statut"], {"a": a.doc_a, "b": a.doc_b, "par_statut": dict(counts)})
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
