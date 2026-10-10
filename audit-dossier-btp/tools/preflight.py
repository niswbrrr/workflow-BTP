#!/usr/bin/env python3
"""Phase 0 — vérification de l'environnement et préparation du répertoire de sortie.

Usage :
  python preflight.py --source <dossier> [--sortie <dossier_sortie>] [--mode standard]

- ne modifie jamais le dossier source ;
- choisit un répertoire de sortie NEUF (livrables_audit, livrables_audit-2, ...) :
  aucun fichier existant n'est écrasé ;
- recense les bibliothèques disponibles et en déduit les capacités de lecture.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from btp_common import TOOLS_VERSION, journal, now_iso, print_summary, save_json  # noqa: E402

SUBDIRS = ["extraits", "controles", "constats", "echanges", "verification", "arbitrage",
           "decisions", "qualite"]


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def choose_output(base: Path) -> Path:
    if not base.exists():
        return base
    for i in range(2, 1000):
        cand = base.with_name(f"{base.name}-{i}")
        if not cand.exists():
            return cand
    raise RuntimeError("impossible de trouver un nom de répertoire de sortie libre")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--mode", default="standard")
    a = ap.parse_args()

    warnings: list[str] = []
    src = Path(os.path.expanduser(a.source)).resolve()
    summary = {"statut": "ok", "outil": "preflight", "version_outils": TOOLS_VERSION,
               "horodatage": now_iso(), "python": platform.python_version(),
               "systeme": f"{platform.system()} {platform.release()}", "mode": a.mode}

    if sys.version_info < (3, 9):
        summary["statut"] = "echec"
        summary["erreur"] = "Python 3.9 ou supérieur requis"
        print_summary(summary)
        return 0

    if not src.exists():
        summary.update(statut="echec", erreur=f"dossier source introuvable : {src}")
        print_summary(summary)
        return 0

    files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    summary["source"] = {"chemin": str(src), "est_dossier": src.is_dir(), "nb_fichiers": len(files),
                         "taille_octets": total}
    if not files:
        summary.update(statut="echec", erreur="le dossier source ne contient aucun fichier")
        print_summary(summary)
        return 0

    base = Path(os.path.expanduser(a.sortie)).resolve() if a.sortie else (Path.cwd() / "livrables_audit")
    out = choose_output(base)
    if out != base:
        warnings.append(f"{base} existe déjà : sortie redirigée vers {out} (rien n'est écrasé)")
    src_dir = src if src.is_dir() else src.parent
    try:
        out.relative_to(src_dir)
        warnings.append("le répertoire de sortie est situé dans le dossier source : il sera exclu de l'inventaire")
    except ValueError:
        pass
    work = out / "_travail"
    for d in SUBDIRS:
        (work / d).mkdir(parents=True, exist_ok=True)

    libs = {m: has_module(m) for m in ["pdfplumber", "pypdf", "pypdfium2", "openpyxl", "docx",
                                       "ifcopenshell", "jsonschema"]}
    caps = {
        "pdf_texte": "pdfplumber" if libs["pdfplumber"] else ("pypdf" if libs["pypdf"] else None),
        "xlsx": "openpyxl" if libs["openpyxl"] else "stdlib",
        "docx": "python-docx" if libs["docx"] else "stdlib",
        "ifc": "stdlib (lecture STEP partielle)",
        "csv_txt_md": "stdlib",
    }
    if caps["pdf_texte"] is None:
        warnings.append("aucune bibliothèque PDF (pdfplumber/pypdf) : le texte des PDF ne sera pas extrait, "
                        "les agents liront les PDF directement et les citations PDF ne pourront pas être "
                        "vérifiées automatiquement. Installation suggérée (à faire par l'utilisateur) : "
                        "pip install --user pdfplumber")
    if not libs["openpyxl"]:
        warnings.append("openpyxl absent : lecture XLSX par repli bibliothèque standard ; pas de classeur "
                        "Excel en sortie (CSV uniquement)")

    summary.update(sortie=str(out), travail=str(work), bibliotheques=libs, capacites=caps,
                   avertissements=warnings)
    save_json(work / "preflight.json", summary)
    journal(work, "preflight", "ok", {"source": str(src), "sortie": str(out), "capacites": caps})
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
