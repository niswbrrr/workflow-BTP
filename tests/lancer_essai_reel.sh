#!/usr/bin/env bash
# Essai RÉEL (vrais agents, consomme des jetons) du workflow sur le dossier d'essai fictif.
# Usage : tests/lancer_essai_reel.sh [rapide|standard|approfondi] [répertoire_de_travail]
# Le workflow est copié dans un projet temporaire pour ne rien écrire dans le dépôt.
set -euo pipefail
MODE="${1:-rapide}"
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
TRAVAIL="${2:-$(mktemp -d)}"
mkdir -p "$TRAVAIL/.claude/workflows"
cp "$RACINE/.claude/workflows/audit-dossier-btp.js" "$TRAVAIL/.claude/workflows/"
cd "$TRAVAIL"
[ -d .git ] || git init -q .
echo "Essai réel en mode $MODE dans $TRAVAIL (journal : $TRAVAIL/log.jsonl)"
CLAUDE_CODE_WORKFLOWS=1 claude -p "/audit-dossier-btp $RACINE/tests/dossier_test mode=$MODE outils=$RACINE/audit-dossier-btp/tools" \
  --add-dir "$RACINE" --permission-mode acceptEdits \
  --allowedTools "Workflow" "Bash" "Read" "Write" "Edit" "Grep" "Glob" \
  --settings '{"enableWorkflows":true}' --output-format stream-json --verbose < /dev/null > "$TRAVAIL/log.jsonl"
echo "Terminé. Livrables : $TRAVAIL/livrables_audit/"
