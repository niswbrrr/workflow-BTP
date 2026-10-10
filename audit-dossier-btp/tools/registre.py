#!/usr/bin/env python3
"""Registre central des constats — reconstruction déterministe et rejouable.

Le registre est TOUJOURS reconstruit à partir des fichiers produits par les agents :
  _travail/constats/*.json            constats (collecte, synthèse, complétude)
  _travail/decisions/fusions.json     décisions de fusion (juge de dédoublonnage)
  _travail/echanges/rN/a_traiter.json transmissions routées au tour N
  _travail/echanges/rN/<agent>.json   réponses des destinataires au tour N
  _travail/verification/*.json        verdicts des vérificateurs adversariaux
  _travail/arbitrage/*.json           arbitrages des désaccords
Aucun statut final n'est fixé par un agent : il est calculé par les règles ci-dessous.

Sous-commandes :
  validate      --fichier F --type constats|reponses|verification|arbitrage|fusions|synthese|revue|classement
                [--travail W] [--agent CLE] [--actifs a,b,c]
  build         --travail W
  transmissions --travail W --round N --actifs a,b,c [--cap 6]
  selection     --travail W --mode rapide|standard|approfondi [--nouveaux-seulement]

Règles de statut (dans l'ordre) :
  retrait par l'auteur                                  -> refute
  arbitrage présent                                     -> selon la décision (maintenu=corrobore,
                                                           rejete=refute, requalifie/desaccord=non_resolu)
  confirmations ET réfutations                          -> conteste (arbitrage requis)
  réfutations sans confirmation                         -> refute
  verdicts « insuffisant » ≥ confirmations              -> non_resolu (requalifié question_ouverte)
  confirmations (vérificateur, pair indépendant, outil) -> corrobore
  détection indépendante par ≥ 2 agents                 -> corrobore
  sinon                                                 -> a_verifier
"""
from __future__ import annotations

import argparse
import ast
import json
import operator
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from btp_common import (jaccard, journal, load_json, load_schema, norm_text,  # noqa: E402
                        now_iso, print_summary, quote_found, read_extract_pages, save_json, tokens,
                        validate_schema)

SEV_ORDER = {"critique": 0, "majeure": 1, "moderee": 2, "mineure": 3}
PRIO_ORDER = {"P1": 0, "P2": 1, "P3": 2}
CONF_ORDER = ["faible", "moyenne", "elevee"]
CORRIGEABLES = {"severity", "severity_criteria", "severity_rationale", "priority", "finding_type", "confidence",
                "confidence_rationale", "claim", "title", "lot", "recommended_action", "open_questions",
                "counterarguments", "economic_impact", "calculation", "technical_impact", "decision_deadline",
                "responsible_party"}
LENSES = ["provenance", "calcul", "interpretation"]
VOTES = {  # nombre de vérificateurs par gravité et par mode
    "rapide": {"critique": 1, "majeure": 1, "moderee": 0, "mineure": 0},
    "standard": {"critique": 3, "majeure": 2, "moderee": 1, "mineure": 0},
    "approfondi": {"critique": 3, "majeure": 3, "moderee": 2, "mineure": 1},
}
CAP_VERIF = {"rapide": 10, "standard": 30, "approfondi": 80}


# ------------------------------------------------------------------ contexte ---

class Ctx:
    def __init__(self, work: Path):
        self.work = work
        self.manifest = load_json(work / "manifeste.json", {"documents": []})
        self.docs = {d["doc_id"]: d for d in self.manifest.get("documents", [])}
        self.classement = load_json(work / "manifeste_classe.json", None)
        self._pages = {}
        self.controls = {}
        for p in sorted((work / "controles").glob("dpgf_*.json")):
            data = load_json(p, {})
            for c in data.get("controles", []):
                self.controls[c["controle_id"]] = {**c, "outil": "dpgf_check", "fichier": str(p)}
        for p in sorted((work / "controles").glob("rapprochement_*.json")):
            data = load_json(p, {})
            for c in data.get("lignes", []):
                self.controls[c["controle_id"]] = {**c, "outil": "rapprochement", "fichier": str(p)}

    def pages(self, doc_id):
        if doc_id not in self._pages:
            d = self.docs.get(doc_id)
            self._pages[doc_id] = read_extract_pages(d["extrait"]) if d and d.get("extrait") else None
        return self._pages[doc_id]


# --------------------------------------------------------------- preuves ---

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def safe_eval(expr: str, variables: dict):
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        raise ValueError(f"élément non autorisé : {ast.dump(node)[:60]}")
    expr = expr.replace("×", "*").replace("÷", "/").replace(",", ".")
    if "=" in expr:
        expr = expr.split("=")[0]
    return ev(ast.parse(expr.strip(), mode="eval"))


def numeric_vars(variables):
    out = {}
    for k, v in (variables or {}).items():
        if isinstance(v, dict):
            v = v.get("valeur")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = float(v)
    return out


def check_sources(f, ctx):
    flags, checked = [], []
    for s in f.get("sources", []):
        s = dict(s)
        did = s.get("doc_id")
        if did == "EXT":
            s["verification"] = "source_externe" if s.get("url") else "source_externe_sans_url"
            if not s.get("url"):
                flags.append("source_externe_sans_reference")
            checked.append(s)
            continue
        doc = ctx.docs.get(did)
        if doc is None:
            s["verification"] = "document_inconnu"
            flags.append("source_inconnue")
            checked.append(s)
            continue
        pp = s.get("page_pdf")
        if isinstance(pp, int) and doc.get("nb_pages") and (pp < 1 or pp > doc["nb_pages"]):
            s["verification"] = "page_hors_document"
            flags.append("page_hors_document")
            checked.append(s)
            continue
        cit = s.get("citation")
        if not cit:
            s["verification"] = "sans_citation"
        else:
            pages = ctx.pages(did)
            if not pages:
                s["verification"] = "non_verifiable_sans_extrait"
            elif isinstance(pp, int) and pp in pages and quote_found(cit, pages[pp][1]):
                s["verification"] = "citation_verifiee"
            elif any(quote_found(cit, t) for _, t in pages.values()):
                s["verification"] = "citation_verifiee_autre_page" if isinstance(pp, int) else "citation_verifiee"
                if isinstance(pp, int):
                    flags.append("page_citation_inexacte")
            else:
                s["verification"] = "citation_non_retrouvee"
                flags.append("citation_non_retrouvee")
        checked.append(s)
    return checked, flags


def check_calc(f, ctx):
    calc = f.get("calculation")
    if not calc:
        return None, []
    cid = calc.get("controle_id")
    res = calc.get("resultat")
    if cid:
        rec = ctx.controls.get(cid)
        if rec is None:
            return "controle_introuvable", ["controle_introuvable"]
        if res is None:
            return "controle_verifie", []
        nums = [v for k, v in rec.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
                and k not in ("ligne", "ligne_a", "ligne_b", "score_libelle")]
        if any(abs(res - v) <= max(0.01, 0.005 * abs(v)) for v in nums):
            return "controle_verifie", []
        return "controle_incoherent", ["calcul_incoherent_avec_outil"]
    if calc.get("formule") and res is not None:
        try:
            val = safe_eval(calc["formule"], numeric_vars(calc.get("variables")))
        except Exception:
            return "non_recalculable", ["formule_non_recalculable"]
        if abs(val - res) <= max(0.01, 0.005 * abs(res)):
            return "recalcule_ok", []
        return "recalcule_ko", ["calcul_faux"]
    return "non_recalculable", []


def evidence_level(sources, calc_state):
    if calc_state == "controle_verifie":
        return "prouve_par_outil"
    if any(s.get("verification") == "citation_verifiee" for s in sources):
        return "citation_verifiee"
    if any(s.get("verification") in ("citation_verifiee_autre_page",) for s in sources):
        return "citation_verifiee"
    ok = [s for s in sources if s.get("verification") not in ("document_inconnu", "page_hors_document",
                                                               "citation_non_retrouvee", "source_externe_sans_url")]
    if any((s.get("page") or s.get("page_pdf") or s.get("localisation")) for s in ok):
        return "observation_localisee"
    return "non_etaye"


def downgrade(conf):
    i = CONF_ORDER.index(conf) if conf in CONF_ORDER else 1
    return CONF_ORDER[max(0, i - 1)]


# ---------------------------------------------------------------- lecture ---

def read_files(work: Path, ctx: Ctx):
    sch = load_schema("constats.schema.json")
    findings, agents, invalid, transmissions = [], {}, [], []
    seen_ids = {}
    for p in sorted((work / "constats").glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            invalid.append({"fichier": p.name, "erreurs": [f"JSON illisible : {exc}"]})
            continue
        top_errors = validate_schema({k: v for k, v in data.items() if k != "constats"} | {"constats": []}, sch)
        if top_errors:
            invalid.append({"fichier": p.name, "erreurs": top_errors[:15]})
            continue
        fsch = sch["properties"]["constats"]["items"]
        agent = data["agent"]
        ids = []
        bad = []
        for i, f in enumerate(data.get("constats", [])):
            errs = validate_schema(f, fsch, f"$.constats[{i}]")
            if errs:
                bad.append({"index": i, "finding_id": f.get("finding_id"), "erreurs": errs[:8]})
                continue
            f = dict(f)
            fid = f["finding_id"]
            if fid in seen_ids:
                fid = f"{fid}-{agent[:6].replace('_', '')}"
                f["finding_id"] = fid
            seen_ids[fid] = agent
            f["_agent"] = agent
            f["_phase"] = data["phase"]
            f["_fichier"] = p.name
            findings.append(f)
            ids.append(fid)
        if bad:
            invalid.append({"fichier": p.name, "constats_rejetes": bad})
        agents.setdefault(agent, {"fichiers": [], "constats": [], "documents_examines": [], "ras": [],
                                  "limites": [], "lacunes": [], "statuts": []})
        a = agents[agent]
        a["fichiers"].append(p.name)
        a["constats"].extend(ids)
        a["documents_examines"].extend(data.get("documents_examines", []))
        a["ras"].extend(data.get("ras", []))
        a["limites"].extend(data.get("limites", []))
        a["lacunes"].extend(data.get("lacunes", []))
        a["statuts"].append({"phase": data["phase"], "statut_analyse": data["statut_analyse"],
                             "motif": data.get("motif_statut")})
        if data["phase"] in ("collecte", "synthese"):
            counter = Counter()
            for t in data.get("transmissions", []):
                key = t.get("constat_id") or "g"
                counter[key] += 1
                transmissions.append({"transmission_id": f"T1-{agent}-{key}-{counter[key]}", "round": 1,
                                      "de": agent, **t})
    return findings, agents, invalid, transmissions


def read_responses(work: Path):
    sch = load_schema("reponses.schema.json")
    out, invalid = [], []
    for d in sorted((work / "echanges").glob("r*")):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            if p.name == "a_traiter.json":
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                invalid.append({"fichier": f"{d.name}/{p.name}", "erreurs": [f"JSON illisible : {exc}"]})
                continue
            errs = validate_schema(data, sch)
            if errs:
                invalid.append({"fichier": f"{d.name}/{p.name}", "erreurs": errs[:15]})
                continue
            data["_fichier"] = f"{d.name}/{p.name}"
            out.append(data)
    return out, invalid


def read_dir(work: Path, sub: str, schema_name: str):
    sch = load_schema(schema_name)
    out, invalid = [], []
    for p in sorted((work / sub).glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            invalid.append({"fichier": f"{sub}/{p.name}", "erreurs": [f"JSON illisible : {exc}"]})
            continue
        errs = validate_schema(data, sch)
        if errs:
            invalid.append({"fichier": f"{sub}/{p.name}", "erreurs": errs[:15]})
            continue
        data["_fichier"] = p.name
        out.append(data)
    return out, invalid


# ----------------------------------------------------------------- fusion ---

def source_keys(f):
    keys = set()
    for s in f.get("sources", []):
        keys.add((s.get("doc_id"), s.get("page_pdf") or s.get("page") or s.get("localisation")))
    c = (f.get("calculation") or {}).get("controle_id")
    if c:
        keys.add(("CTRL", c))
    return keys


def merge_group(fs, preferes=frozenset()):
    fs = sorted(fs, key=lambda f: (0 if f["finding_id"] in preferes else 1, SEV_ORDER.get(f["severity"], 9),
                                   -len(f.get("sources", [])), f["finding_id"]))
    p = dict(fs[0])
    p["merged_from"] = [f["finding_id"] for f in fs[1:]]
    p["origin_agents"] = sorted({a for f in fs for a in f["origin_agents"]})
    p["severity"] = min((f["severity"] for f in fs), key=lambda s: SEV_ORDER.get(s, 9))
    p["priority"] = min((f["priority"] for f in fs), key=lambda s: PRIO_ORDER.get(s, 9))
    for key in ("evidence", "counterarguments", "open_questions", "dependencies"):
        seen, merged = set(), []
        for f in fs:
            for x in f.get(key, []) or []:
                k = json.dumps(x, sort_keys=True, ensure_ascii=False)
                if k not in seen:
                    seen.add(k)
                    merged.append(x)
        p[key] = merged
    seen, srcs = set(), []
    for f in fs:
        for s in f.get("sources", []):
            k = (s.get("doc_id"), s.get("page_pdf"), s.get("page"), s.get("localisation"), s.get("citation"))
            if k not in seen:
                seen.add(k)
                srcs.append(s)
    p["sources"] = srcs
    if not p.get("calculation"):
        p["calculation"] = next((f["calculation"] for f in fs if f.get("calculation")), None)
    chiffres = [f for f in fs if (f.get("economic_impact") or {}).get("quantifie")]
    if chiffres and not (p.get("economic_impact") or {}).get("quantifie"):
        e = dict(chiffres[0]["economic_impact"])
        e["commentaire"] = ((e.get("commentaire") or "") + f" (chiffrage repris de {chiffres[0]['finding_id']})").strip()
        p["economic_impact"] = e
    autres = [f["finding_id"] for f in chiffres if f["economic_impact"] != p.get("economic_impact")
              and f["economic_impact"].get("montant_ht") != (p.get("economic_impact") or {}).get("montant_ht")]
    if autres:
        p.setdefault("quality_flags", []).append("impacts_divergents_entre_constats_fusionnes")
    p["versions_fusionnees"] = [{"finding_id": f["finding_id"], "agent": f["_agent"], "title": f["title"],
                                 "claim": f["claim"]} for f in fs[1:]]
    return p


def find_candidates(findings, decided):
    cands = []
    for i in range(len(findings)):
        for j in range(i + 1, len(findings)):
            a, b = findings[i], findings[j]
            pair = tuple(sorted((a["finding_id"], b["finding_id"])))
            if pair in decided:
                continue
            ca = (a.get("calculation") or {}).get("controle_id")
            cb = (b.get("calculation") or {}).get("controle_id")
            same_ctrl = bool(ca and ca == cb)
            shared = source_keys(a) & source_keys(b)
            lot_ok = (not a["lot"] or not b["lot"] or norm_text(a["lot"])[:6] == norm_text(b["lot"])[:6])
            st = jaccard(tokens(a["title"]), tokens(b["title"]))
            sc = jaccard(tokens(a["claim"]), tokens(b["claim"]))
            score = max(st, sc)
            if same_ctrl or (shared and lot_ok and score >= 0.3) or (lot_ok and score >= 0.55):
                cands.append({"ids": list(pair), "score_libelle": round(score, 2), "sources_communes": len(shared),
                              "meme_controle": same_ctrl,
                              "a": {"finding_id": a["finding_id"], "agent": a["_agent"], "title": a["title"],
                                    "lot": a["lot"], "type": a["finding_type"]},
                              "b": {"finding_id": b["finding_id"], "agent": b["_agent"], "title": b["title"],
                                    "lot": b["lot"], "type": b["finding_type"]}})
    return cands


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


# ----------------------------------------------------------------- statut ---

def compute_status(f):
    if f.get("retrait"):
        return "refute", f"retiré par son auteur : {f['retrait']['motif']}"
    arb = f.get("arbitrage")
    if arb:
        dec = arb["decision"]
        if dec in ("maintenu", "rejete") and not arb.get("elements_decisifs"):
            f.setdefault("quality_flags", []).append("arbitrage_sans_element_decisif")
            return "non_resolu", "arbitrage rendu sans élément décisif : désaccord maintenu"
        return {"maintenu": ("corrobore", "maintenu après arbitrage"),
                "rejete": ("refute", "rejeté après arbitrage"),
                "requalifie": ("non_resolu", "requalifié après arbitrage"),
                "desaccord_persistant": ("non_resolu", "désaccord persistant après arbitrage")}[dec]
    votes = f.get("verifications", [])
    peer = [e for e in f.get("echanges", []) if e.get("verdict") and e.get("independant")]
    tool = f.get("evidence_level") == "prouve_par_outil"
    c = sum(1 for v in votes if v["verdict"] in ("confirme", "reformuler")) + \
        sum(1 for e in peer if e["verdict"] == "confirme") + (1 if tool else 0)
    r = sum(1 for v in votes if v["verdict"] == "refute") + sum(1 for e in peer if e["verdict"] == "refute")
    i = sum(1 for v in votes if v["verdict"] == "insuffisant")
    if r and c:
        return "conteste", f"{c} confirmation(s) contre {r} réfutation(s) : arbitrage requis"
    if r:
        return "refute", f"{r} réfutation(s), aucune confirmation"
    vc = sum(1 for v in votes if v["verdict"] in ("confirme", "reformuler"))
    if i and i >= vc and not tool:
        return "non_resolu", f"{i} vérificateur(s) jugent la preuve insuffisante"
    if c:
        src = []
        if vc:
            src.append(f"{vc} vérificateur(s)")
        if any(e["verdict"] == "confirme" for e in peer):
            src.append("pair indépendant")
        if tool:
            src.append("contrôle déterministe")
        return "corrobore", "confirmé par " + ", ".join(src)
    if len(f.get("origin_agents", [])) >= 2:
        return "corrobore", "détecté indépendamment par plusieurs agents"
    return "a_verifier", "non vérifié de façon indépendante"


# ------------------------------------------------------------------ build ---

def build(work: Path):
    ctx = Ctx(work)
    findings, agents, invalid, transmissions = read_files(work, ctx)
    responses, inv_r = read_responses(work)
    verifs, inv_v = read_dir(work, "verification", "verification.schema.json")
    arbits, inv_a = read_dir(work, "arbitrage", "arbitrage.schema.json")
    fusions = load_json(work / "decisions" / "fusions.json", {"decisions": []})
    invalid += inv_r + inv_v + inv_a

    # constats issus des réponses (nouveaux constats d'échange)
    for resp in responses:
        rnd = resp["round"]
        counter = Counter()
        for f in resp.get("constats", []):
            f = dict(f)
            if any(x["finding_id"] == f["finding_id"] for x in findings):
                f["finding_id"] = f"{f['finding_id']}-r{rnd}"
            f.update(_agent=resp["agent"], _phase="echanges", _fichier=resp["_fichier"])
            findings.append(f)
            agents.setdefault(resp["agent"], {"fichiers": [], "constats": [], "documents_examines": [], "ras": [],
                                              "limites": [], "lacunes": [], "statuts": []})
            agents[resp["agent"]]["constats"].append(f["finding_id"])
        for t in resp.get("transmissions", []):
            key = t.get("constat_id") or "g"
            counter[key] += 1
            transmissions.append({"transmission_id": f"T{rnd + 1}-{resp['agent']}-{key}-{counter[key]}",
                                  "round": rnd + 1, "de": resp["agent"], **t})
        if resp["agent"] in agents:
            agents[resp["agent"]]["limites"].extend(resp.get("limites", []))

    # preuves
    for f in findings:
        f["origin_agents"] = [f["_agent"]]
        f["finding_type_initial"] = f["finding_type"]
        f["confidence_initiale"] = f["confidence"]
        srcs, flags = check_sources(f, ctx)
        calc_state, cflags = check_calc(f, ctx)
        f["sources"] = srcs
        f["calcul_verification"] = calc_state
        f["quality_flags"] = sorted(set(flags + cflags))

    # fusions décidées + fusions automatiques (même contrôle déterministe et même type)
    uf = UF()
    decided = set()
    auto = []
    preferes = frozenset(d["id_retenu"] for d in fusions.get("decisions", [])
                         if d.get("decision") == "fusionner" and d.get("id_retenu"))
    for d in fusions.get("decisions", []):
        ids = sorted(d["ids"])
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                decided.add((ids[x], ids[y]))
        if d["decision"] == "fusionner":
            for x in ids[1:]:
                uf.union(ids[0], x)
    by_ctrl = defaultdict(list)
    for f in findings:
        c = (f.get("calculation") or {}).get("controle_id")
        if c:
            by_ctrl[(c, f["finding_type"])].append(f["finding_id"])
    for (c, _), ids in by_ctrl.items():
        if len(ids) > 1:
            ids = sorted(ids)
            for x in ids[1:]:
                if tuple(sorted((ids[0], x))) not in decided:
                    uf.union(ids[0], x)
                    auto.append({"ids": [ids[0], x], "motif": f"même contrôle déterministe {c}"})
    groups = defaultdict(list)
    for f in findings:
        groups[uf.find(f["finding_id"])].append(f)
    merged, remap = [], {}
    for _, fs in groups.items():
        m = merge_group(fs, preferes) if len(fs) > 1 else fs[0]
        m.setdefault("merged_from", [])
        for f in fs:
            remap[f["finding_id"]] = m["finding_id"]
        if len(fs) > 1:
            srcs, flags = check_sources(m, ctx)
            m["sources"] = srcs
            m["quality_flags"] = sorted(set(sum((f.get("quality_flags", []) for f in fs), []) + flags))
        merged.append(m)
    findings = merged
    index = {f["finding_id"]: f for f in findings}
    for f in findings:
        f["dependencies"] = sorted({remap.get(d, d) for d in f.get("dependencies", []) if remap.get(d, d) != f["finding_id"]})

    # niveau de preuve et requalification
    for f in findings:
        lvl = evidence_level(f["sources"], f.get("calcul_verification"))
        f["evidence_level"] = lvl
        if "citation_non_retrouvee" in f["quality_flags"] or "calcul_faux" in f["quality_flags"]:
            f["confidence"] = downgrade(f["confidence"])
        if f["finding_type"] == "anomalie_averee":
            distinct = {s.get("doc_id") for s in f["sources"] if s.get("verification") not in
                        ("document_inconnu", "page_hors_document", "citation_non_retrouvee")}
            if lvl == "non_etaye":
                f["finding_type"] = "question_ouverte"
                f["quality_flags"].append("requalifie_non_etaye")
            elif lvl == "observation_localisee" and len(distinct) < 2:
                f["finding_type"] = "incoherence"
                f["quality_flags"].append("requalifie_preuve_insuffisante")
        elif lvl == "non_etaye" and f["finding_type"] not in ("question_ouverte", "hypothese"):
            f["quality_flags"].append("non_etaye")

    # transmissions et réponses
    for t in transmissions:
        t["constat_id_registre"] = remap.get(t.get("constat_id"), t.get("constat_id"))
    tindex = {t["transmission_id"]: t for t in transmissions}
    for resp in responses:
        agent = resp["agent"]
        for r in resp.get("reponses", []):
            t = tindex.get(r["transmission_id"])
            target = remap.get(r.get("constat_id") or (t or {}).get("constat_id"))
            if t is not None:
                t["reponse"] = {"verdict": r["verdict"], "par": agent, "fichier": resp["_fichier"]}
            if target in index:
                f = index[target]
                f.setdefault("echanges", []).append({
                    "round": resp["round"], "transmission_id": r["transmission_id"],
                    "de": (t or {}).get("de"), "a": agent, "question": (t or {}).get("question"),
                    "verdict": r["verdict"], "justification": r["justification"],
                    "elements_nouveaux": r.get("elements_nouveaux", []), "sources": r.get("sources", []),
                    "independant": agent not in f["origin_agents"]})
        for c in resp.get("corrections", []):
            target = remap.get(c["finding_id"])
            if target not in index:
                continue
            f = index[target]
            if agent not in f["origin_agents"]:
                f["quality_flags"].append("correction_refusee_non_auteur")
                continue
            applied = {k: v for k, v in c["champs"].items() if k in CORRIGEABLES}
            for k, v in applied.items():
                if k in ("counterarguments", "open_questions") and isinstance(v, list):
                    f[k] = list(dict.fromkeys((f.get(k) or []) + v))
                else:
                    f[k] = v
            f.setdefault("corrections", []).append({"par": agent, "round": resp["round"], "champs": applied,
                                                    "motif": c["motif"]})
        for rt in resp.get("retraits", []):
            target = remap.get(rt["finding_id"])
            if target in index and agent in index[target]["origin_agents"]:
                index[target]["retrait"] = {"par": agent, "motif": rt["motif"]}

    # vérifications et arbitrages
    for v in verifs:
        target = remap.get(v["constat_id"], v["constat_id"])
        if target in index:
            index[target].setdefault("verifications", []).append(
                {k: v.get(k) for k in ("lentille", "verdict", "justification", "elements_nouveaux", "sources",
                                       "correction_proposee", "confiance")} | {"fichier": v["_fichier"]})
    for a in arbits:
        target = remap.get(a["constat_id"], a["constat_id"])
        if target in index:
            index[target]["arbitrage"] = {k: a.get(k) for k in ("decision", "motif", "elements_decisifs",
                                                                 "sources", "nouveau_type", "positions",
                                                                 "questions_pour_moe")}
            if a["decision"] == "requalifie" and a.get("nouveau_type"):
                index[target]["finding_type"] = a["nouveau_type"]

    # statuts
    for f in findings:
        st, why = compute_status(f)
        f["status"] = st
        f["motif_statut"] = why
        if st == "non_resolu" and "insuffisant" in why and f["finding_type"] not in ("question_ouverte",):
            f["finding_type"] = "question_ouverte"
            f["quality_flags"].append("requalifie_question_par_verification")
        if f["severity"] in ("critique", "majeure") and f["confidence"] == "faible" and st == "a_verifier":
            f["quality_flags"].append("verification_rapide_recommandee")
        f["quality_flags"] = sorted(set(f["quality_flags"]))
        f["phase_origine"] = f.pop("_phase", None)
        f["agent_origine"] = f.pop("_agent", None)
        f["fichier_origine"] = f.pop("_fichier", None)

    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), PRIO_ORDER.get(f["priority"], 9), f["finding_id"]))
    cands = find_candidates([dict(f, _agent=f["agent_origine"]) for f in findings if f["status"] != "refute"], decided)
    coverage = compute_coverage(ctx, findings, agents)

    reg = {"genere_le": now_iso(), "nb_constats": len(findings), "constats": findings,
           "transmissions": transmissions, "agents": agents, "fichiers_invalides": invalid,
           "fusions_automatiques": auto, "doublons_candidats": cands, "correspondance_ids": remap,
           "couverture": coverage}
    save_json(work / "registre.json", reg)
    save_json(work / "couverture.json", coverage)
    stats = {"par_statut": dict(Counter(f["status"] for f in findings)),
             "par_type": dict(Counter(f["finding_type"] for f in findings)),
             "par_gravite": dict(Counter(f["severity"] for f in findings))}
    journal(work, "registre.build", "ok" if not invalid else "partiel",
            {"nb_constats": len(findings), **stats, "fichiers_invalides": len(invalid)})
    return reg, stats


# -------------------------------------------------------------- couverture ---

def compute_coverage(ctx, findings, agents):
    examined = defaultdict(set)
    for name, a in agents.items():
        for d in a["documents_examines"]:
            examined[d["doc_id"]].add(f"{name}:{d['profondeur']}")
    cited = defaultdict(set)
    for f in findings:
        for s in f.get("sources", []):
            if s.get("doc_id") in ctx.docs:
                cited[s["doc_id"]].add(f["finding_id"])
    dup_of = {}
    for group in ctx.manifest.get("doublons_exacts", []):
        for d in group[1:]:
            dup_of[d] = group[0]
    never, unusable = [], []
    for did, d in ctx.docs.items():
        if d.get("extraction") in ("non_pris_en_charge", "archive_non_extraite", "erreur_lecture"):
            unusable.append({"doc_id": did, "nom": d["chemin_relatif"], "extraction": d["extraction"]})
        if not examined.get(did) and not cited.get(did):
            if did in dup_of and (examined.get(dup_of[did]) or cited.get(dup_of[did])):
                continue
            never.append({"doc_id": did, "nom": d["chemin_relatif"], "format": d["format"],
                          "extraction": d.get("extraction")})
    lots_manifest = {l["lot"]: l["intitules"] for l in ctx.manifest.get("lots_mentionnes", [])}
    covered_text = " ".join(norm_text(f.get("lot", "")) for f in findings) + " " + " ".join(
        norm_text(r.get("sujet", "")) for a in agents.values() for r in a["ras"])
    lots_sans = []
    for lot, names in lots_manifest.items():
        keys = [norm_text(n).split(" ")[0] for n in names if n] + [f"lot {lot}", f"lot {lot.zfill(2)}"]
        if not any(k and k in covered_text for k in keys):
            lots_sans.append({"lot": lot, "intitules": names})
    agents_bloques = [{"agent": n, **s} for n, a in agents.items() for s in a["statuts"]
                      if s["statut_analyse"] != "terminee"]
    unverified = [f["finding_id"] for f in findings if f["status"] == "a_verifier"
                  and f["severity"] in ("critique", "majeure")]
    return {"documents_jamais_examines": never, "documents_non_exploitables": unusable,
            "documents_examines": {k: sorted(v) for k, v in examined.items()},
            "lots_sans_analyse_explicite": lots_sans, "agents_non_termines": agents_bloques,
            "constats_graves_non_verifies": unverified,
            "citations_non_retrouvees": [f["finding_id"] for f in findings
                                         if "citation_non_retrouvee" in f.get("quality_flags", [])]}


# -------------------------------------------------------------- commandes ---

def cmd_validate(a):
    schema_name = f"{a.type}.schema.json"
    sch = load_schema(schema_name)
    try:
        data = json.loads(Path(a.fichier).read_text(encoding="utf-8"))
    except Exception as exc:
        print_summary({"statut": "invalide", "erreurs": [f"JSON illisible : {exc}"]})
        return 0
    errors = validate_schema(data, sch)
    warnings = []
    if a.type in ("constats", "reponses") and not errors:
        ids = [f["finding_id"] for f in data.get("constats", [])]
        dup = [i for i, n in Counter(ids).items() if n > 1]
        if dup:
            errors.append(f"identifiants en double : {dup}")
        if a.agent and data.get("agent") != a.agent:
            errors.append(f"agent « {data.get('agent')} » ≠ attendu « {a.agent} »")
        actifs = set(a.actifs.split(",")) if a.actifs else None
        for t in data.get("transmissions", []):
            if actifs and t["destinataire"] not in actifs:
                warnings.append(f"transmission vers « {t['destinataire']} » : agent inactif (elle sera reportée "
                                f"dans les questions à arbitrer)")
            if t.get("constat_id") and t["constat_id"] not in ids and a.type == "constats":
                warnings.append(f"transmission sur {t['constat_id']} : identifiant absent de ce fichier")
        if a.travail:
            ctx = Ctx(Path(a.travail))
            for f in data.get("constats", []):
                srcs, flags = check_sources(f, ctx)
                state, cflags = check_calc(f, ctx)
                for fl in sorted(set(flags + cflags)):
                    warnings.append(f"{f['finding_id']} : {fl}")
                if not f.get("sources"):
                    warnings.append(f"{f['finding_id']} : aucune source (le constat sera requalifié)")
    print_summary({"statut": "ok" if not errors else "invalide", "erreurs": errors[:40],
                   "avertissements": warnings[:40]})
    return 0


def cmd_build(a):
    work = Path(a.travail).resolve()
    reg, stats = build(work)
    per_agent = {k: v["constats"] for k, v in reg["agents"].items()}
    summary = {"statut": "ok" if not reg["fichiers_invalides"] else "partiel", "outil": "registre.build",
               "nb_constats": reg["nb_constats"], **stats,
               "fichiers_invalides": reg["fichiers_invalides"][:20],
               "constats_par_agent": per_agent,
               "fusions_automatiques": len(reg["fusions_automatiques"]),
               "doublons_candidats": [{k: c[k] for k in ("ids", "score_libelle", "sources_communes", "meme_controle")}
                                      | {"titres": [c["a"]["title"], c["b"]["title"]]}
                                      for c in reg["doublons_candidats"][:40]],
               "nb_doublons_candidats": len(reg["doublons_candidats"]),
               "contestes": [f["finding_id"] for f in reg["constats"] if f["status"] == "conteste"],
               "couverture": {"documents_jamais_examines": [d["doc_id"] for d in reg["couverture"]["documents_jamais_examines"]],
                              "lots_sans_analyse_explicite": [l["lot"] for l in reg["couverture"]["lots_sans_analyse_explicite"]],
                              "agents_non_termines": [x["agent"] for x in reg["couverture"]["agents_non_termines"]],
                              "constats_graves_non_verifies": reg["couverture"]["constats_graves_non_verifies"],
                              "citations_non_retrouvees": reg["couverture"]["citations_non_retrouvees"]},
               "transmissions_par_round": dict(Counter(t["round"] for t in reg["transmissions"])),
               "registre": str(work / "registre.json")}
    print_summary(summary)
    return 0


def cmd_transmissions(a):
    work = Path(a.travail).resolve()
    reg = load_json(work / "registre.json")
    if reg is None:
        reg, _ = build(work)
    actifs = set(a.actifs.split(",")) if a.actifs else set()
    index = {f["finding_id"]: f for f in reg["constats"]}
    todo = [t for t in reg["transmissions"] if t["round"] == a.round]
    seen = set()
    groups = defaultdict(list)
    ecartees = []
    for t in todo:
        key = (t["destinataire"], t.get("constat_id_registre"), norm_text(t["question"])[:80])
        if key in seen:
            ecartees.append({"transmission_id": t["transmission_id"], "motif": "doublon de question"})
            continue
        seen.add(key)
        if t["destinataire"] not in actifs:
            ecartees.append({"transmission_id": t["transmission_id"], "motif": "destinataire inactif",
                             "destinataire": t["destinataire"], "question": t["question"]})
            continue
        if t["destinataire"] == t["de"]:
            ecartees.append({"transmission_id": t["transmission_id"], "motif": "auto-transmission"})
            continue
        f = index.get(t.get("constat_id_registre"))
        if f is not None and f["status"] == "refute":
            ecartees.append({"transmission_id": t["transmission_id"], "motif": "constat déjà réfuté"})
            continue
        groups[t["destinataire"]].append((t, f))
    out = {"round": a.round, "par_destinataire": {}, "ecartees": ecartees}
    for dest, items in sorted(groups.items()):
        items.sort(key=lambda tf: (SEV_ORDER.get((tf[1] or {}).get("severity"), 5),
                                   PRIO_ORDER.get((tf[1] or {}).get("priority"), 5), tf[0]["transmission_id"]))
        kept, dropped = items[:a.cap], items[a.cap:]
        for t, _ in dropped:
            ecartees.append({"transmission_id": t["transmission_id"], "motif": f"plafond de {a.cap} questions "
                             f"par destinataire atteint", "destinataire": dest, "question": t["question"]})
        out["par_destinataire"][dest] = [{
            "transmission_id": t["transmission_id"], "de": t["de"], "constat_id": t.get("constat_id_registre"),
            "question": t["question"], "raison": t.get("raison"),
            "constat": None if f is None else {k: f.get(k) for k in ("title", "claim", "lot", "finding_type",
                                                                      "severity", "status", "sources")}}
            for t, f in kept]
    d = work / "echanges" / f"r{a.round}"
    d.mkdir(parents=True, exist_ok=True)
    save_json(d / "a_traiter.json", out)
    journal(work, "registre.transmissions", "ok", {"round": a.round,
                                                    "destinataires": {k: len(v) for k, v in out["par_destinataire"].items()},
                                                    "ecartees": len(ecartees)})
    print_summary({"statut": "ok", "outil": "registre.transmissions", "round": a.round,
                   "fichier": str(d / "a_traiter.json"),
                   "par_destinataire": {k: [x["transmission_id"] for x in v] for k, v in out["par_destinataire"].items()},
                   "ecartees": [{k: e.get(k) for k in ("transmission_id", "motif", "destinataire")} for e in ecartees][:40]})
    return 0


def cmd_selection(a):
    work = Path(a.travail).resolve()
    reg = load_json(work / "registre.json")
    if reg is None:
        reg, _ = build(work)
    mode = a.mode if a.mode in VOTES else "standard"
    cands = []
    for f in reg["constats"]:
        if f.get("retrait"):
            continue
        refute_par_pair = f["status"] == "refute" and not f.get("verifications") and not f.get("arbitrage")
        if f["status"] == "refute" and not refute_par_pair:
            continue
        if a.nouveaux_seulement and f.get("verifications"):
            continue
        n = VOTES[mode].get(f["severity"], 0)
        if f["severity"] == "moderee" and mode == "standard" and not (
                f["priority"] == "P1" or (f.get("economic_impact") or {}).get("quantifie")):
            n = 0
        if f["severity"] == "mineure" and mode == "approfondi" and f["priority"] != "P1":
            n = 0
        if f["status"] == "conteste":
            n = max(n, {"rapide": 1, "standard": 2, "approfondi": 3}[mode])
        if refute_par_pair and f["severity"] in ("critique", "majeure", "moderee"):
            n = max(n, 1)  # une réfutation par un seul pair est elle-même contrôlée
        if f["evidence_level"] == "prouve_par_outil":
            n = min(n, 1)
        if n == 0:
            continue
        if f.get("calculation") or f["finding_type"] == "anomalie_averee":
            order = ["calcul", "provenance", "interpretation"]
        elif f["finding_type"] in ("omission_possible", "incoherence", "risque"):
            order = ["interpretation", "provenance", "calcul"]
        else:
            order = ["provenance", "interpretation", "calcul"]
        peer = [e for e in f.get("echanges", []) if e.get("independant")]
        cands.append({"finding_id": f["finding_id"], "title": f["title"], "severity": f["severity"],
                      "priority": f["priority"], "status": f["status"], "lentilles": order[:n],
                      "prouve_par_outil": f["evidence_level"] == "prouve_par_outil",
                      "confirmations_pairs": sum(1 for e in peer if e["verdict"] == "confirme"),
                      "refutations_pairs": sum(1 for e in peer if e["verdict"] == "refute"),
                      "origin_agents": f["origin_agents"]})
    cands.sort(key=lambda c: (SEV_ORDER.get(c["severity"], 9), 0 if c["status"] == "conteste" else 1,
                              PRIO_ORDER.get(c["priority"], 9), c["finding_id"]))
    cap = CAP_VERIF[mode] if a.cap is None else min(CAP_VERIF[mode], max(0, a.cap))
    sel, dropped = cands[:cap], cands[cap:]
    out = {"mode": mode, "selection": sel, "non_verifies_plafond": [c["finding_id"] for c in dropped]}
    save_json(work / "selection_verification.json", out)
    journal(work, "registre.selection", "ok", {"mode": mode, "selection": len(sel), "plafond_depasse": len(dropped)})
    print_summary({"statut": "ok", "outil": "registre.selection", **out})
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--fichier", required=True)
    v.add_argument("--type", default="constats", choices=["constats", "reponses", "verification", "arbitrage",
                                                          "fusions", "synthese", "revue", "classement"])
    v.add_argument("--travail", default=None)
    v.add_argument("--agent", default=None)
    v.add_argument("--actifs", default=None)
    b = sub.add_parser("build")
    b.add_argument("--travail", required=True)
    t = sub.add_parser("transmissions")
    t.add_argument("--travail", required=True)
    t.add_argument("--round", type=int, required=True)
    t.add_argument("--actifs", default="")
    t.add_argument("--cap", type=int, default=6)
    s = sub.add_parser("selection")
    s.add_argument("--travail", required=True)
    s.add_argument("--mode", default="standard")
    s.add_argument("--nouveaux-seulement", action="store_true")
    s.add_argument("--cap", type=int, default=None, help="plafond de constats à vérifier (imposé par le budget)")
    a = ap.parse_args()
    return {"validate": cmd_validate, "build": cmd_build, "transmissions": cmd_transmissions,
            "selection": cmd_selection}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
