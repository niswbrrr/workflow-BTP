#!/usr/bin/env python3
"""Installe le workflow audit-dossier-btp dans l'espace PERSONNEL de Claude Code.

Usage :
  python install.py                      installation dans ~/.claude (ou $CLAUDE_CONFIG_DIR)
  python install.py --cible <dossier>    installation dans un autre répertoire de configuration
  python install.py --forcer             remplace une version existante (l'ancienne est sauvegardée)
  python install.py --activer-workflows  ajoute "enableWorkflows": true à settings.json (sauvegarde faite)
  python install.py --verifier           contrôle une installation existante sans rien écrire

Ce qui est copié :
  <cible>/workflows/audit-dossier-btp.js          le workflow (commande /audit-dossier-btp)
  <cible>/audit-dossier-btp/tools/*.py            outils déterministes
  <cible>/audit-dossier-btp/schemas/*.json        contrat de données
Rien d'autre n'est modifié ni supprimé ; aucune dépendance n'est installée.
"""
from __future__ import annotations

import argparse
import datetime
import filecmp
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
WF = ICI / ".claude" / "workflows" / "audit-dossier-btp.js"
OUTILS = ICI / "audit-dossier-btp" / "tools"
SCHEMAS = ICI / "audit-dossier-btp" / "schemas"


def cible_par_defaut() -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


def plan(cible: Path):
    paires = [(WF, cible / "workflows" / WF.name)]
    paires += [(p, cible / "audit-dossier-btp" / "tools" / p.name) for p in sorted(OUTILS.glob("*.py"))]
    paires += [(p, cible / "audit-dossier-btp" / "schemas" / p.name) for p in sorted(SCHEMAS.glob("*.json"))]
    return paires


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cible", default=None)
    ap.add_argument("--forcer", action="store_true")
    ap.add_argument("--activer-workflows", action="store_true")
    ap.add_argument("--verifier", action="store_true")
    a = ap.parse_args()
    cible = Path(a.cible).expanduser().resolve() if a.cible else cible_par_defaut()
    if sys.version_info < (3, 9):
        print("Python 3.9 ou supérieur est requis.")
        return 1
    paires = plan(cible)
    manquants = [s for s, _ in paires if not s.exists()]
    if manquants:
        print("Fichiers sources introuvables (lancer depuis le dépôt workflow-BTP) :", *manquants, sep="\n  ")
        return 1

    differents = [(s, d) for s, d in paires if d.exists() and not filecmp.cmp(s, d, shallow=False)]
    if a.verifier:
        absents = [d for _, d in paires if not d.exists()]
        print(f"Cible : {cible}")
        print(f"  fichiers installés : {len(paires) - len(absents)}/{len(paires)}")
        print(f"  fichiers différents du dépôt : {len(differents)}")
        for _, d in differents:
            print(f"    - {d}")
        return 0 if not absents and not differents else 2

    if differents and not a.forcer:
        print("Une autre version est déjà installée ; rien n'a été modifié. Fichiers différents :")
        for _, d in differents:
            print(f"  - {d}")
        print("Relancez avec --forcer pour la remplacer (une sauvegarde .bak-<date> sera créée).")
        return 2

    horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for s, d in paires:
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists() and not filecmp.cmp(s, d, shallow=False):
            sauvegarde = d.with_name(d.name + f".bak-{horodatage}")
            shutil.copy2(d, sauvegarde)
            print(f"  sauvegarde : {sauvegarde}")
        shutil.copy2(s, d)
    print(f"Installé dans {cible} ({len(paires)} fichiers).")

    if a.activer_workflows:
        reglages = cible / "settings.json"
        donnees = {}
        if reglages.exists():
            try:
                donnees = json.loads(reglages.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"{reglages} n'est pas un JSON valide : non modifié. Activez « Dynamic workflows » via /config.")
                donnees = None
            if donnees is not None:
                shutil.copy2(reglages, reglages.with_name(f"settings.json.bak-{horodatage}"))
        if donnees is not None:
            donnees["enableWorkflows"] = True
            reglages.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"« enableWorkflows »: true écrit dans {reglages} (sauvegarde créée si le fichier existait).")

    # contrôle de fumée : les outils se lancent avec l'interpréteur courant
    r = subprocess.run([sys.executable, str(cible / "audit-dossier-btp" / "tools" / "registre.py"), "--help"],
                       capture_output=True, text=True)
    print("Contrôle des outils :", "ok" if r.returncode == 0 else f"échec ({r.stderr.strip()[:200]})")
    print("\nUtilisation dans n'importe quel projet Claude Code :")
    print('  /audit-dossier-btp "<chemin du dossier>" mode=standard')
    print("Prérequis : les « Dynamic workflows » doivent être actifs (/config, ou --activer-workflows).")
    print("Bibliothèques Python conseillées (facultatives, à installer vous-même) : pdfplumber openpyxl python-docx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
