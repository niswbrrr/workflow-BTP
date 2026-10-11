#!/usr/bin/env python3
"""Résume en Markdown les sessions Claude Code imbriquées (`claude -p …`) lancées depuis une session.

Usage :
  python scripts/journal/annexe_sessions_imbriquees.py --scratchpad <dossier> --taches <dossier> \\
         --debut 2026-10-10T23:08:06 --fin 2026-10-11T00:08:06 --sortie annexe.md \\
         [--noms probe sonde reel ...] [--projets ~/.claude/projects] [--masquer-mot Prénom ...]

Sources lues (lecture seule) :
- `<scratchpad>/<nom>/log*.jsonl` et `sortie.jsonl` : journaux stream-json des sessions imbriquées ;
- `<projets>/*scratchpad-<nom>/*.jsonl` : transcription de la session imbriquée (hors sous-agents) ;
- `<projets>/*scratchpad-<nom>/*/subagents/workflows/wf_*/journal.jsonl` et `agent-<id>.jsonl` :
  journal du workflow et transcriptions des agents (horodatages de début et de fin) ;
- `<taches>/*.output` : sorties des tâches d'arrière-plan de la session principale.

Les adresses de courriel (hors adresse publique des commits) et les mots désignés sont masqués ;
les espaces de fin de ligne sont supprimés.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re

RE_COURRIEL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PUBLICS = {"noreply@anthropic.com"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratchpad", required=True)
    ap.add_argument("--taches", required=True)
    ap.add_argument("--projets", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--debut", required=True)
    ap.add_argument("--fin", required=True)
    ap.add_argument("--noms", nargs="+", default=["probe", "sonde", "reel", "reel2", "perso", "plug"])
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--masquer-mot", action="append", default=[])
    a = ap.parse_args()
    mots = [re.compile(rf"\b{re.escape(m)}\b") for m in a.masquer_mot]

    def m(s: str) -> str:
        s = RE_COURRIEL.sub(lambda x: x.group(0) if x.group(0) in PUBLICS else "[masqué : adresse de courriel]", s)
        for motif in mots:
            s = motif.sub("[masqué : donnée personnelle]", s)
        return s

    out = ["# Annexe — sessions Claude Code imbriquées lancées pendant la session", "",
           "Exécutions non interactives (`claude -p …`) lancées par Claude depuis la session principale pour "
           "éprouver le workflow sur le moteur réel. Sources : journaux `stream-json` écrits dans le répertoire "
           "temporaire de la session (`<scratchpad>/<nom>/log*.jsonl`, `sortie.jsonl`), transcriptions de session "
           "et de sous-agents sous `~/.claude/projects/-tmp-…-scratchpad-<nom>/`, journal du workflow "
           "(`journal.jsonl`). Ces fichiers sont dans un conteneur éphémère et ne sont pas versionnés : cette "
           "annexe en conserve l'essentiel vérifiable. Générée par `scripts/journal/annexe_sessions_imbriquees.py`.",
           "",
           f"Période étudiée : {a.debut}Z → {a.fin}Z. « Fenêtre » : position de la session imbriquée par rapport "
           "à cette période, d'après les horodatages de sa propre transcription.", "",
           "Les textes « Réponse finale de la session imbriquée » sont écrits par le modèle de la session "
           "imbriquée : ce sont des déclarations, pas des preuves. Les tableaux d'agents viennent des journaux "
           "du moteur et font foi en cas de divergence.", ""]
    for nom in a.noms:
        trouves = glob.glob(os.path.join(a.projets, f"*scratchpad-{nom}"))
        if not trouves:
            continue
        P = trouves[0]
        ts, prompts = [], []
        for f in glob.glob(P + "/*.jsonl"):
            for ligne in open(f, encoding="utf-8"):
                e = json.loads(ligne)
                t = e.get("timestamp")
                if t:
                    ts.append(t)
                c = (e.get("message") or {}).get("content")
                if e.get("type") == "user" and isinstance(c, str) and e.get("promptSource") != "system" \
                        and not c.startswith("<"):
                    prompts.append((t, c[:300]))
        logs = sorted(glob.glob(f"{a.scratchpad}/{nom}/log*.jsonl") + glob.glob(f"{a.scratchpad}/{nom}/sortie.jsonl"))
        couts, outils, textes = [], [], []
        for lg in logs:
            for ligne in open(lg, encoding="utf-8"):
                try:
                    e = json.loads(ligne)
                except ValueError:
                    continue
                b = os.path.basename(lg)
                if e.get("type") == "result":
                    couts.append((b, e.get("total_cost_usd"), e.get("num_turns"), e.get("duration_ms"), e.get("is_error")))
                if e.get("type") == "assistant":
                    for bloc in e["message"]["content"]:
                        if bloc.get("type") == "tool_use":
                            outils.append((b, bloc["name"], json.dumps(bloc["input"], ensure_ascii=False)[:300]))
                        if bloc.get("type") == "text":
                            textes.append((b, bloc["text"]))
        deb, fin = (min(ts), max(ts)) if ts else (None, None)
        fen = ("hors (avant)" if fin and fin[:19] < a.debut else
               "dans" if deb and deb[:19] >= a.debut else "chevauche le début" if deb else "?")
        out += [f"## Exécution « {nom} »", "", f"- Fenêtre : {fen}",
                f"- Premier / dernier horodatage de la session imbriquée (hors sous-agents) : {deb} → {fin}",
                f"- Répertoire de transcription : `~/.claude/projects/{os.path.basename(P)}/`"]
        for t, p in prompts[:3]:
            out.append(f"- Requête transmise (horodatage {t}) : `{m(p)}`")
        for lg, c, nt, du, er in couts:
            out.append(f"- Résultat `{lg}` : coût {c} $ ; tours {nt} ; durée API {du} ms ; erreur {er}")
        for lg, n, i in outils:
            out.append(f"- Outil appelé par la session imbriquée (`{lg}`) : `{n}` `{m(i)}`")
        for lg, t in textes:
            out += [f"- Réponse finale de la session imbriquée (`{lg}`) :", "", "```text", m(t), "```", ""]
        for J in sorted(glob.glob(P + "/*/subagents/workflows/wf_*/journal.jsonl")):
            D = os.path.dirname(J)
            lignes = [json.loads(x) for x in open(J, encoding="utf-8")]
            demarres = {e["agentId"]: e for e in lignes if e.get("type") == "started"}
            res = {e["agentId"]: e.get("result") for e in lignes if e.get("type") == "result"}
            out += ["", f"### Workflow `{os.path.basename(D)}` : {len(demarres)} agent(s) lancés", "",
                    "| # | Agent (label) | Phase | Début (UTC) | Fin (UTC) | Résultat renvoyé (extrait) |",
                    "|---|---|---|---|---|---|"]
            for i, (aid, e) in enumerate(demarres.items(), 1):
                f = f"{D}/agent-{aid}.jsonl"
                t = [json.loads(x).get("timestamp") for x in open(f, encoding="utf-8")] if os.path.exists(f) else []
                t = [x for x in t if x]
                r = res.get(aid)
                if isinstance(r, dict):
                    cles = [k for k in ("statut", "validation", "verdict", "decision", "statut_analyse", "fusions", "messages") if k in r]
                    ext = "; ".join(f"{k}={r[k]}" for k in cles)
                    if isinstance(r.get("constats"), list):
                        ext += f"; constats={len(r['constats'])}"
                    if isinstance(r.get("reponses"), list):
                        ext += f"; réponses={len(r['reponses'])}"
                elif r is None:
                    ext = "(aucun résultat enregistré)"
                else:
                    ext = str(r)[:80]
                out.append(f"| {i} | {e['label']} | {e.get('phase', '')} | {min(t) if t else '?'} | "
                           f"{max(t) if t else '?'} | {m(ext).replace('|', '/')} |")
            autres = sorted({x.get("type") for x in lignes if x.get("type") not in ("started", "result")})
            if autres:
                out.append(f"\nAutres entrées du journal : {', '.join(autres)}")
        out.append("")
    out += ["## Sorties des tâches d’arrière-plan de la session principale", "",
            "Fichiers `tasks/<id>.output` (sortie standard des commandes lancées en arrière-plan ou des moniteurs). "
            "La date de modification du fichier est un indice, pas la preuve de l'heure d'une action.", ""]
    for f in sorted(glob.glob(os.path.join(a.taches, "*.output"))):
        mt = datetime.datetime.fromtimestamp(os.stat(f).st_mtime, datetime.timezone.utc)
        out += [f"### `{os.path.basename(f)}` — modifié {mt.strftime('%Y-%m-%dT%H:%M:%S')}Z (date de fichier, indicative)",
                "", "```text", m(open(f, errors="replace").read()), "```", ""]
    with open(a.sortie, "w", encoding="utf-8") as s:
        s.write("\n".join(l.rstrip() for l in "\n".join(out).splitlines()).rstrip("\n") + "\n")
    print("ok", len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
