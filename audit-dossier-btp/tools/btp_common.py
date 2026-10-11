"""Fonctions communes aux outils déterministes du workflow audit-dossier-btp.

Principes :
- bibliothèque standard d'abord ; pdfplumber / pypdf / openpyxl / python-docx sont
  utilisés seulement s'ils sont installés, sinon un repli est employé ou la limite
  est déclarée ;
- aucun fichier source n'est jamais modifié : les outils lisent le dossier source
  et écrivent uniquement dans le répertoire de travail ;
- chaque exécution d'outil est tracée dans _travail/journal_controles.jsonl.
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TOOLS_VERSION = "1.0.0"


# ---------------------------------------------------------------- E/S JSON ---

def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, data) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, p)


def print_summary(data) -> None:
    """Imprime le résumé compact destiné à l'orchestrateur (stdout, UTF-8)."""
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(out)


def journal(work, outil: str, statut: str, details=None) -> None:
    """Ajoute une ligne au journal des contrôles (append-only)."""
    if work is None:
        return
    p = Path(work) / "journal_controles.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"horodatage": now_iso(), "outil": outil, "version": TOOLS_VERSION,
           "statut": statut, "details": details or {}}
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ------------------------------------------------------------- Normalisation ---

_QUOTES = str.maketrans({"’": "'", "‘": "'", "«": '"', "»": '"',
                         "“": '"', "”": '"', "–": "-", "—": "-",
                         " ": " ", " ": " ", " ": " "})


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_text(s: str) -> str:
    """Normalisation tolérante pour comparer des citations et des libellés."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).translate(_QUOTES)
    s = strip_accents(s).lower()
    s = re.sub(r"-\s*\n\s*", "", s)          # césure de fin de ligne
    s = re.sub(r"[^\w%€.,/+'\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


STOPWORDS = {"de", "du", "des", "la", "le", "les", "et", "en", "a", "au", "aux", "pour", "sur",
             "par", "un", "une", "y", "compris", "yc", "d", "l", "dans", "avec", "sans", "ou"}


def tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", norm_text(s)) if t and t not in STOPWORDS]


def jaccard(a, b) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ------------------------------------------------------------------ Nombres ---

_NUM_CLEAN = re.compile(r"[\s  €$]|(eur(os)?|ht|ttc)$", re.I)


def parse_number(v):
    """Interprète un nombre au format français ou anglais. Retourne float ou None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    s = _NUM_CLEAN.sub("", s.lower())
    s = s.replace("%", "")
    if not s or not re.fullmatch(r"[-+]?[\d.,']+", s):
        return None
    s = s.replace("'", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_fr(n, dec=2) -> str:
    """Format numérique français pour CSV Excel (virgule décimale, sans séparateur de milliers)."""
    if n is None or n == "":
        return ""
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    if dec == 0 or (abs(f - round(f)) < 1e-9 and dec <= 2 and abs(f) >= 1e6):
        return str(int(round(f)))
    return f"{f:.{dec}f}".replace(".", ",")


# ------------------------------------------------------------------- Unités ---

_UNIT_ALIASES = {
    "m2": {"m2", "m²", "m^2", "mc", "metre carre", "metres carres", "m carre"},
    "m3": {"m3", "m³", "m^3", "metre cube", "metres cubes"},
    "ml": {"ml", "m", "m.l", "m.l.", "mlin", "metre lineaire", "metres lineaires", "lm"},
    "u": {"u", "un", "unite", "unites", "nb", "nbre", "pce", "pc", "piece", "pieces", "ex", "ens.u"},
    "ens": {"ens", "ensemble", "ft", "fft", "forfait", "f", "global", "gl", "glob"},
    "kg": {"kg", "kgs", "kilo", "kilogramme"},
    "t": {"t", "tonne", "tonnes", "to"},
    "h": {"h", "heure", "heures", "hr"},
    "j": {"j", "jour", "jours"},
    "l": {"l", "litre", "litres"},
    "pm": {"pm", "p.m.", "p.m", "pour memoire", "memoire"},
}
_UNIT_INDEX = {alias: canon for canon, aliases in _UNIT_ALIASES.items() for alias in aliases}


def norm_unit(u):
    if u is None:
        return None
    s = strip_accents(unicodedata.normalize("NFKC", str(u))).strip().lower()
    s = s.replace("²", "2").replace("³", "3")
    s = re.sub(r"\s+", " ", s)
    if not s:
        return None
    return _UNIT_INDEX.get(s, _UNIT_INDEX.get(s.replace(" ", ""), "?" + s))


def units_compatible(a, b) -> bool:
    if a is None or b is None:
        return True
    return norm_unit(a) == norm_unit(b)


# ------------------------------------------------------ Lecture de tableaux ---

def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
       "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


def read_xlsx_stdlib(path):
    """Lecteur XLSX minimal (valeurs en cache uniquement), sans dépendance."""
    sheets = []
    formulas_without_cache = 0
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", _NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", _NS)}
        for sh in wb.findall("m:sheets/m:sheet", _NS):
            rid = sh.get("{%s}id" % _NS["r"])
            tgt = target.get(rid, "")
            tgt = tgt.lstrip("/")
            if not tgt.startswith("xl/"):
                tgt = "xl/" + tgt
            root = ET.fromstring(z.read(tgt))
            rows = []
            for row in root.iter("{%s}row" % _NS["m"]):
                rnum = int(row.get("r", len(rows) + 1))
                cells = {}
                for c in row.findall("m:c", _NS):
                    ref = c.get("r")
                    t = c.get("t")
                    v = c.find("m:v", _NS)
                    f = c.find("m:f", _NS)
                    val = None
                    if t == "s" and v is not None:
                        val = shared[int(v.text)]
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter("{%s}t" % _NS["m"]))
                    elif v is not None:
                        val = v.text
                    elif f is not None:
                        formulas_without_cache += 1
                    if ref is not None and val is not None:
                        cells[_col_index(ref)] = val
                if cells:
                    width = max(cells) + 1
                    rows.append((rnum, [cells.get(i, "") for i in range(width)]))
            sheets.append({"name": sh.get("name"), "rows": rows})
    return sheets, formulas_without_cache


def read_xlsx(path):
    try:
        import openpyxl  # type: ignore
    except ImportError:
        return read_xlsx_stdlib(path)
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheets = []
    for ws in wb.worksheets:
        rows = []
        for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            vals = ["" if v is None else v for v in row]
            while vals and vals[-1] == "":
                vals.pop()
            if any(str(v).strip() for v in vals):
                rows.append((r_idx, vals))
        sheets.append({"name": ws.title, "rows": rows})
    wb.close()
    # openpyxl en data_only renvoie None pour une formule sans cache : on recompte via le lecteur brut
    try:
        _, missing = read_xlsx_stdlib(path)
    except Exception:
        missing = 0
    return sheets, missing


def read_csv_table(path):
    raw = Path(path).read_bytes()
    text = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    delim = ";"
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        if sample.count(";") < sample.count(","):
            delim = ","
    rows = []
    for i, row in enumerate(csv.reader(io.StringIO(text), delimiter=delim), start=1):
        if any(c.strip() for c in row):
            rows.append((i, row))
    return [{"name": Path(path).stem, "rows": rows}], 0


def read_table(path):
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if ext in (".csv", ".tsv", ".txt"):
        return read_csv_table(path)
    raise ValueError(f"format de tableau non pris en charge : {ext}")


HEADER_KEYS = {
    "ref": ["n°", "n", "no", "num", "numero", "art", "article", "ref", "reference", "poste", "code", "item", "repere"],
    "designation": ["designation", "libelle", "description", "ouvrage", "prestation", "intitule", "nature des ouvrages"],
    "unite": ["u", "unite", "unit", "un"],
    "quantite": ["qte", "quantite", "qt", "quant", "quantites", "qte totale", "quantite totale"],
    "pu": ["pu", "p.u", "prix unitaire", "pu ht", "p.u. ht", "prix u", "prix unitaire ht", "pu (eur ht)"],
    "montant": ["montant", "total", "prix total", "montant ht", "total ht", "prix total ht", "montant (eur ht)"],
}


def _header_score(cells):
    found = {}
    for idx, cell in enumerate(cells):
        c = norm_text(cell).strip(" .:")
        if not c:
            continue
        for key, words in HEADER_KEYS.items():
            if key in found:
                continue
            for w in words:
                if c == w or (len(w) > 3 and c.startswith(w)) or (key == "montant" and "montant" in c) \
                        or (key == "pu" and ("prix unitaire" in c or c.startswith("p.u") or c.startswith("pu "))) \
                        or (key == "quantite" and (c.startswith("qte") or c.startswith("quantit"))):
                    found[key] = idx
                    break
    return found


def detect_header(rows, max_scan=40, overrides=None):
    """Retourne (index_ligne_entete, mapping colonnes) ou (None, {})."""
    best = (None, {})
    for i, (_, cells) in enumerate(rows[:max_scan]):
        found = _header_score(cells)
        if len(found) > len(best[1]) and "designation" in found:
            best = (i, found)
    if overrides:
        mapping = dict(best[1])
        mapping.update({k: v for k, v in overrides.items() if v is not None})
        return best[0], mapping
    return best


def cell(cells, idx):
    if idx is None or idx >= len(cells):
        return ""
    v = cells[idx]
    return "" if v is None else v


# --------------------------------------------------------------- Schémas ---

def _type_ok(value, t):
    if isinstance(t, list):
        return any(_type_ok(value, x) for x in t)
    return {
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "null": value is None,
    }.get(t, True)


def validate_schema(value, schema, path="$", errors=None, max_errors=60):
    """Validateur JSON Schema minimal (sous-ensemble utilisé par le workflow)."""
    if errors is None:
        errors = []
    if len(errors) >= max_errors:
        return errors
    t = schema.get("type")
    if t is not None and not _type_ok(value, t):
        errors.append(f"{path}: type attendu {t}, obtenu {type(value).__name__}")
        return errors
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: valeur {value!r} hors liste {schema['enum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: chaîne trop courte (min {schema['minLength']})")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: chaîne trop longue (max {schema['maxLength']})")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: ne respecte pas le motif {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: valeur < {schema['minimum']}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: champ obligatoire manquant « {req} »")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                validate_schema(v, props[k], f"{path}.{k}", errors, max_errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: champ non prévu « {k} »")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: au moins {schema['minItems']} élément(s) attendu(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                validate_schema(item, schema["items"], f"{path}[{i}]", errors, max_errors)
    return errors


def schemas_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "schemas"


def load_schema(name: str):
    return load_json(schemas_dir() / name)


# -------------------------------------------------------------- Extraits ---

PAGE_MARK = re.compile(r"^=== PAGE (\d+)(?: \(affichée : ([^)]*)\))? ===$", re.M)


def read_extract_pages(path):
    """Retourne {page_pdf: (page_affichee, texte)} depuis un extrait texte balisé."""
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8", errors="replace")
    pages = {}
    marks = list(PAGE_MARK.finditer(text))
    if not marks:
        return {1: (None, text)}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        pages[int(m.group(1))] = (m.group(2), text[m.end():end])
    return pages


def quote_found(quote: str, text: str) -> bool:
    """Vrai si la citation figure dans le texte (normalisé), avec tolérance de mise en page."""
    q = norm_text(quote)
    t = norm_text(text)
    if not q:
        return False
    if q in t:
        return True
    qt = q.split(" ")
    if len(qt) < 6:
        return False
    tt = " " + t + " "
    grams = [" ".join(qt[i:i + 4]) for i in range(len(qt) - 3)]
    hits = sum(1 for g in grams if (" " + g + " ") in tt)
    return hits / len(grams) >= 0.85
