#!/usr/bin/env python3
"""Extrait une période d'une session Claude Code (fichier JSONL) en transcription Markdown fidèle.

Usage :
  python scripts/journal/extraire_session_claude.py <session.jsonl> --debut 2026-10-10T23:08:06 \\
         --fin 2026-10-11T00:08:06 --sortie-md transcription.md --sortie-json index.json \\
         [--contexte-md contexte.md] [--max-car 12000] [--masquer-mot Prénom ...]

Principes :
- l'ordre est celui du fichier JSONL (chronologique), chaque événement reçoit un identifiant E0001… ;
- messages humains, réponses de Claude, appels d'outils (avec paramètres) et résultats sont recopiés
  tels quels ; rien n'est reformulé ;
- MASQUAGES (tous signalés dans le texte par « [masqué : motif] ») : adresses de courriel (hors
  adresses publiques de l'historique Git), identifiants de compte, noms d'affichage, jetons ;
  rappels et consignes du harnais (balises system-reminder, commentaires HTML des notifications,
  schémas d'outils renvoyés par ToolSearch) ; mots désignés par --masquer-mot (données personnelles
  inutiles, par exemple un prénom employé dans un chemin d'essai) ;
- les blocs de réflexion interne ne sont pas publiés (ils sont d'ailleurs vides dans la trace :
  seule une signature est stockée) ; leur nombre est indiqué ;
- une sortie plus longue que --max-car est coupée en tête et en queue avec un marqueur explicite
  qui donne sa longueur totale et l'empreinte SHA-256 du texte complet (vérification possible) ;
- les espaces de fin de ligne sont supprimés à l'écriture (sans effet sur le sens ; les empreintes
  SHA-256 portent sur le texte avant cette suppression).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

COURRIELS_PUBLICS = {"noreply@anthropic.com", "git@github.com"}
RE_COURRIEL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
RE_CLES_SENSIBLES = re.compile(
    r'("(?:account_uuid|display_name|email|api_token_hint|access_token|refresh_token|password|secret|token)"\s*:\s*)"[^"]*"',
    re.I)
RE_JETONS = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,})\b")
RE_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}")
RE_RAPPEL = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
RE_COMMENTAIRE = re.compile(r"<!--.*?-->", re.S)
MASQUAGES = Counter()
MOTS_PERSONNELS: list[re.Pattern] = []


def masquer(texte: str) -> str:
    if not isinstance(texte, str):
        texte = json.dumps(texte, ensure_ascii=False, indent=2)

    def courriel(m):
        if m.group(0).lower() in COURRIELS_PUBLICS:
            return m.group(0)
        MASQUAGES["adresse de courriel"] += 1
        return "[masqué : adresse de courriel]"

    def rappel(_m):
        MASQUAGES["rappel système du harnais"] += 1
        return "[masqué : rappel système du harnais]"

    def cle(m):
        MASQUAGES["identifiant de compte ou jeton"] += 1
        return m.group(1) + '"[masqué]"'

    def jeton(_m):
        MASQUAGES["jeton"] += 1
        return "[masqué : jeton]"

    texte = RE_RAPPEL.sub(rappel, texte)
    texte = RE_CLES_SENSIBLES.sub(cle, texte)
    texte = RE_JETONS.sub(jeton, texte)
    texte = RE_BEARER.sub(lambda m: m.group(1) + "[masqué : jeton]", texte)
    texte = RE_COURRIEL.sub(courriel, texte)
    for motif in MOTS_PERSONNELS:
        texte, nb = motif.subn("[masqué : donnée personnelle]", texte)
        MASQUAGES["donnée personnelle (mot désigné)"] += nb
    return texte


def couper(texte: str, maxi: int) -> str:
    if len(texte) <= maxi:
        return texte
    empreinte = hashlib.sha256(texte.encode("utf-8")).hexdigest()
    tete, queue = texte[: int(maxi * 0.7)], texte[-int(maxi * 0.25):]
    MASQUAGES["sortie coupée (longueur)"] += 1
    return (f"{tete}\n\n[… coupé pour la lisibilité : {len(texte) - len(tete) - len(queue)} caractères omis sur "
            f"{len(texte)} ; SHA-256 du texte complet (après masquage) : {empreinte} …]\n\n{queue}")


def texte_resultat(contenu) -> str:
    if isinstance(contenu, str):
        return contenu
    morceaux = []
    for b in contenu or []:
        if b.get("type") == "text":
            morceaux.append(b.get("text", ""))
        else:
            morceaux.append(f"[bloc {b.get('type')} non textuel]")
    return "\n".join(morceaux)


def resultat_special(outil: str, texte: str) -> str:
    """Retire les consignes du harnais tout en gardant les données vérifiables."""
    if outil == "ToolSearch":
        noms = re.findall(r'"name":\s*"([^"]+)"', texte)
        MASQUAGES["schémas d'outils (ToolSearch)"] += 1
        return f"[masqué : schémas d'outils renvoyés] outils chargés : {', '.join(dict.fromkeys(noms)) or '(aucun)'}\n" + \
            ("\n".join(l for l in texte.splitlines() if l.startswith("No matching")) if "No matching" in texte else "")
    if outil == "ReadNotifications":
        garde = []
        for ligne in RE_COMMENTAIRE.sub("[masqué : consignes du harnais]", texte).splitlines():
            if ligne.startswith("Exactly"):
                # partie factuelle (nombre, heure de lecture) ; la suite de la ligne est une consigne du harnais
                faits = re.match(r"(.*?by this machine's clock\.)", ligne)
                garde.append((faits.group(1) if faits else ligne[:120]) + " [masqué : consignes du harnais]")
            elif (ligne.startswith(("--- Notification", "0 notifications", "    {", "  <event", "<wake"))
                    or "[masqué" in ligne):
                garde.append(ligne)
        MASQUAGES["consignes de notification du harnais"] += 1
        return "\n".join(garde)
    if "<!--" in texte:
        MASQUAGES["consignes du harnais (commentaire)"] += 1
        return RE_COMMENTAIRE.sub("[masqué : consignes du harnais]", texte)
    return texte


def notification(prompt: str) -> dict:
    def balise(nom):
        m = re.search(rf"<{nom}>(.*?)</{nom}>", prompt, re.S)
        return m.group(1).strip() if m else None
    return {k: v for k, v in (("tâche", balise("task-id")), ("statut", balise("status")), ("résumé", balise("summary")),
                              ("événement", balise("event"))) if v}


def bloc_code(texte: str, langage: str = "") -> str:
    clotures = max([len(m) for m in re.findall(r"`{3,}", texte)] + [2]) + 1
    c = "`" * clotures
    return f"{c}{langage}\n{texte}\n{c}"


def sans_espaces_finaux(texte: str) -> str:
    return "\n".join(l.rstrip() for l in texte.splitlines()).rstrip("\n") + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--debut", required=True, help="horodatage UTC inclus, format AAAA-MM-JJTHH:MM:SS")
    ap.add_argument("--fin", required=True)
    ap.add_argument("--sortie-md", required=True)
    ap.add_argument("--sortie-json", required=True)
    ap.add_argument("--contexte-md", default=None, help="index compact des événements antérieurs à la période")
    ap.add_argument("--max-car", type=int, default=12000)
    ap.add_argument("--masquer-mot", action="append", default=[],
                    help="mot entier à masquer partout (répétable), par exemple un prénom")
    a = ap.parse_args()
    MOTS_PERSONNELS.extend(re.compile(rf"\b{re.escape(m)}\b") for m in a.masquer_mot)

    entrees = [json.loads(l) for l in open(a.jsonl, encoding="utf-8")]
    appels = {}
    evenements = []
    reflexions = 0
    internes = Counter()
    contexte = []
    n = 0

    def ajouter(ts, acteur, nature, corps, **extra):
        nonlocal n
        n += 1
        ev = {"id": f"E{n:04d}", "horodatage": ts, "acteur": acteur, "nature": nature, **extra, "corps": corps}
        evenements.append(ev)
        return ev

    for e in entrees:
        ts = (e.get("timestamp") or "")[:23]
        avant = ts and ts[:19] < a.debut
        apres = ts and ts[:19] > a.fin
        if apres:
            break
        t = e.get("type")
        msg = e.get("message") or {}
        contenu = msg.get("content")
        if avant:
            if t == "assistant" and isinstance(contenu, list):
                for b in contenu:
                    if b.get("type") == "tool_use":
                        d = (b.get("input") or {}).get("description") or (b.get("input") or {}).get("subject") or ""
                        contexte.append((ts, b.get("name"), masquer(str(d))[:160]))
            elif t == "user" and isinstance(contenu, str) and e.get("promptSource") == "sdk":
                contexte.append((ts, "MESSAGE UTILISATEUR", masquer(contenu)[:160].replace("\n", " ")))
            continue
        if not ts:
            continue
        if t == "user" and isinstance(contenu, str):
            if e.get("promptSource") == "sdk":
                ajouter(ts, "Utilisateur", "message_utilisateur", masquer(contenu))
            else:
                ajouter(ts, "Harnais", "notification", json.dumps(notification(contenu), ensure_ascii=False, indent=2))
        elif t == "user" and isinstance(contenu, list):
            for b in contenu:
                if b.get("type") == "tool_result":
                    app = appels.get(b.get("tool_use_id"), {})
                    outil = app.get("outil", "?")
                    brut = masquer(resultat_special(outil, texte_resultat(b.get("content"))))
                    nature = "decision_utilisateur" if outil == "AskUserQuestion" else "resultat_outil"
                    ajouter(ts, "Utilisateur" if nature == "decision_utilisateur" else "Outil", nature,
                            couper(brut, a.max_car), outil=outil, appel=app.get("id"),
                            erreur=bool(b.get("is_error")))
                elif b.get("type") == "text":
                    ajouter(ts, "Utilisateur", "message_utilisateur", masquer(b.get("text", "")))
        elif t == "assistant" and isinstance(contenu, list):
            for b in contenu:
                bt = b.get("type")
                if bt == "thinking":
                    reflexions += 1
                elif bt == "text":
                    ajouter(ts, "Claude", "reponse_claude", masquer(b.get("text", "")))
                elif bt == "tool_use":
                    entree = b.get("input") or {}
                    ev = ajouter(ts, "Claude", "appel_outil",
                                 couper(masquer(json.dumps(entree, ensure_ascii=False, indent=2)), a.max_car),
                                 outil=b.get("name"), appel=b.get("id"),
                                 description=masquer(str(entree.get("description") or entree.get("subject") or "")))
                    appels[b.get("id")] = {"outil": b.get("name"), "id": ev["id"]}
        elif t == "attachment":
            at = e.get("attachment") or {}
            k = at.get("type")
            if k == "queued_command":
                ajouter(ts, "Harnais", "notification",
                        masquer(json.dumps(notification(at.get("prompt", "")), ensure_ascii=False, indent=2)))
            elif k == "edited_text_file":
                ajouter(ts, "Harnais", "fichier_modifie_signale", at.get("filename", "?"))
            else:
                internes[k] += 1
        elif t == "system":
            ajouter(ts, "Harnais", "hook", f"{e.get('subtype')} : {e.get('hookCount')} hook(s), erreurs : "
                                          f"{len(e.get('hookErrors') or [])}")
        else:
            internes[t] += 1

    # appariement appel -> résultat
    resultats = {ev["appel"]: ev for ev in evenements if ev["nature"] in ("resultat_outil", "decision_utilisateur")}
    for ev in evenements:
        if ev["nature"] == "appel_outil":
            r = resultats.get(ev["id"])
            ev["resultat"] = r["id"] if r else None
            ev["statut"] = "sans résultat" if not r else ("erreur" if r.get("erreur") else "ok")

    lignes = [f"# Transcription de la session Claude Code — {a.debut} → {a.fin} (UTC)", "",
              f"Source : `{Path(a.jsonl).name}` (session Claude Code, format JSONL). Généré par "
              "`scripts/journal/extraire_session_claude.py`. Ordre : celui du fichier source.", "",
              f"- Événements retranscrits : {len(evenements)} "
              f"({', '.join(f'{k} {v}' for k, v in Counter(ev['nature'] for ev in evenements).items())})",
              f"- Blocs de réflexion interne non publiés : {reflexions} (vides dans la trace : seule une signature est stockée)",
              f"- Entrées internes du harnais non retranscrites : "
              f"{', '.join(f'{k} {v}' for k, v in internes.items()) or 'aucune'}",
              f"- Masquages appliqués : {', '.join(f'{k} ×{v}' for k, v in MASQUAGES.items()) or 'aucun'}", "",
              "Légende des natures : message_utilisateur, reponse_claude, appel_outil, resultat_outil, "
              "decision_utilisateur (réponse à une question), notification (tâche d'arrière-plan ou GitHub), "
              "fichier_modifie_signale, hook. Les espaces de fin de ligne des textes recopiés sont supprimés.", ""]
    titres = {"message_utilisateur": "Message de l'utilisateur", "reponse_claude": "Réponse de Claude",
              "appel_outil": "Appel d'outil", "resultat_outil": "Résultat d'outil", "decision_utilisateur": "Décision de l'utilisateur",
              "notification": "Notification", "fichier_modifie_signale": "Fichier modifié sur disque (signalé par le harnais)",
              "hook": "Hook du harnais"}
    for ev in evenements:
        entete = f"### {ev['id']} · {ev['horodatage']}Z · {ev['acteur']} · {titres[ev['nature']]}"
        if ev.get("outil"):
            entete += f" · `{ev['outil']}`"
        lignes += [f'<a id="{ev["id"].lower()}"></a>', entete, ""]
        if ev["nature"] == "appel_outil":
            if ev.get("description"):
                lignes.append(f"Description : {ev['description']}")
            lignes.append(f"Statut : {ev['statut']} — résultat : "
                          + (f"[{ev['resultat']}](#{ev['resultat'].lower()})" if ev.get("resultat") else "aucun"))
            lignes += ["", bloc_code(ev["corps"], "json"), ""]
        elif ev["nature"] in ("resultat_outil", "decision_utilisateur"):
            lignes.append(f"En réponse à [{ev['appel']}](#{ev['appel'].lower()})" + (" — **is_error**" if ev.get("erreur") else ""))
            lignes += ["", bloc_code(ev["corps"]), ""]
        elif ev["nature"] in ("message_utilisateur", "reponse_claude"):
            lignes += [bloc_code(ev["corps"], "text"), ""]
        else:
            lignes += [bloc_code(ev["corps"]), ""]
    Path(a.sortie_md).write_text(sans_espaces_finaux("\n".join(lignes)), encoding="utf-8")

    index = [{k: v for k, v in ev.items() if k != "corps"} | {"extrait": ev["corps"][:240]} for ev in evenements]
    Path(a.sortie_json).write_text(json.dumps({"source": Path(a.jsonl).name, "debut": a.debut, "fin": a.fin,
                                               "reflexions_non_publiees": reflexions, "internes": internes,
                                               "masquages": MASQUAGES, "evenements": index},
                                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.contexte_md:
        c = [f"# Contexte antérieur à {a.debut} (UTC) — index compact", "",
             "Hors période étudiée. Seuls les horodatages, les noms d'outils et les descriptions courtes "
             "des appels (ou le début des messages humains) sont repris, pour situer le travail.", "",
             "| Horodatage (UTC) | Outil ou message | Description |", "|---|---|---|"]
        for ts, nom, d in contexte:
            d = d.replace("|", "\\|")
            c.append(f"| {ts}Z | {nom} | {d} |")
        Path(a.contexte_md).write_text(sans_espaces_finaux("\n".join(c)), encoding="utf-8")
    print(json.dumps({"evenements": len(evenements), "par_nature": Counter(ev["nature"] for ev in evenements),
                      "reflexions_non_publiees": reflexions, "masquages": MASQUAGES, "contexte": len(contexte)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
