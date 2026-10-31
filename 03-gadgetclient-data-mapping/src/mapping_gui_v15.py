# Gadget Mapping GUI v15
# CSV mapping, validation, invoicing, bordereau and inbox processing.
#
# Save this file to: C:\GadgetClient\mapping_gui_v15.py
# Run GUI:   py C:\GadgetClient\mapping_gui_v15.py
# Run once:  py C:\GadgetClient\mapping_gui_v15.py --once
# Watch:     py C:\GadgetClient\mapping_gui_v15.py --watch --poll 3
#
# Inbox contract:
# C:\GadgetClient\in\
#   Inbox\        ← drop client files here
#   Processed\
#   Failed\
#
# Failure packs:
# Failed\<Category>\YYYY-MM-DD_HHMMSS__<FileName>\
#   <FileName>                (original file)
#   failure_summary.txt
#   failure_details.json
#   detected_headers.txt
#   mapping_used.json
#
# Outputs (unchanged from v10.1):
# out\YYYY-MM\clean_csv\
# out\YYYY-MM\workflow2_*
# out\YYYY-MM\bordereau\

import PySimpleGUI as sg
import json
import csv
import os
import re
import time
import shutil
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import smtplib
from email.message import EmailMessage
from client_db_v15 import (
    resolve_client_identity,
    get_template_fields,
    get_value_map_cover_level,
    get_value_map_cover_type,
    get_email_recipients_override,
)


OPENPYXL_AVAILABLE = True
try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.utils import get_column_letter
except Exception:
    OPENPYXL_AVAILABLE = False

__version__ = "15"
resolved_client_id = None
resolved_client_name = None

# -------------------------
# Base folders
# -------------------------
BASE_DIR = r"C:\GadgetClient"
MAPPINGS_DIR = os.path.join(BASE_DIR, "Mappings")
OUT_DIR_DEFAULT = os.path.join(BASE_DIR, "out")

IN_DIR = os.path.join(BASE_DIR, "in")
INBOX_DIR = os.path.join(IN_DIR, "Inbox")
PROCESSED_DIR = os.path.join(IN_DIR, "Processed")
FAILED_DIR = os.path.join(IN_DIR, "Failed")
INBOX_CONFIG_PATH = os.path.join(IN_DIR, "inbox_config.json")
for p in (MAPPINGS_DIR, OUT_DIR_DEFAULT, INBOX_DIR, PROCESSED_DIR, FAILED_DIR):
    os.makedirs(p, exist_ok=True)

CSV_OUTPUT_DELIMITER = ";"  # Excel UK friendly
VALUE_FUZZY_THRESHOLD = 0.92
ALLOWED_INBOX_EXTS = {".csv"}
RETRY_TMP_DIR = os.path.join(IN_DIR, "_retry_tmp")
os.makedirs(RETRY_TMP_DIR, exist_ok=True)

# -------------------------
# v10.x output structure (month folder is the contract)
# -------------------------
SUBFOLDERS = {
    "clean_csv": "clean_csv",
    "bordereau": "bordereau",
    "workflow2_micro": "workflow2_micro",
    "workflow2_invoice": "workflow2_invoice",
    "workflow2_backup": "workflow2_invoice backup",
    "workflow2_exceptions": "workflow2_exceptions",
    "workflow2_control": "workflow2_control",
}

CLEAN_NAME_RE = re.compile(
    r"^(?P<client_name>.+?)\.(?P<client_id>[^.]+)\.(?P<month>\d{4}-\d{2})\s+\(Clean\)\.csv$",
    re.IGNORECASE
)

STANDARDISED_NAME_RE = re.compile(
    r"^standardised\.(?P<client_id>[^.]+)\.(?P<client_name>[^.]+)\.(?P<month>\d{4}-\d{2})\.csv$",
    re.IGNORECASE
)

# -------------------------
# Standard fields (Workflow 1 output)
# -------------------------
STANDARD_FIELDS = [
    "Client ID",
    "Client Name",
    "Uniqueid",
    "Firstname",
    "Surname",
    "Add1",
    "Add2",
    "Add3",
    "City",
    "County",
    "Postcode",
    "Email",
    "CoverLevel",
    "CoverType",
    "Start",
    "End",
    "pcm",
]

CANONICAL_COVERLEVEL = {"Standard", "Premier"}
CANONICAL_COVERTYPE = {"Employee Only", "Employee and Partner", "Employee and Family"}

# -------------------------
# Text cleaning / encoding helpers
# -------------------------
def clean_text(s):
    if s is None:
        return ""
    s = str(s)
    return s.replace("Â£", "£").replace("Â", "")

def norm(s: str) -> str:
    if s is None:
        return ""
    return " ".join(clean_text(str(s)).strip().lower().split())

def norm_key(s: str) -> str:
    s = norm(s)
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("’", "'")
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalise_map_keys(d: dict) -> dict:
    return {norm_key(k): v for k, v in d.items()}

## Start Client Database Integration 09012026##

def _normalise_map_keys_local(d: dict) -> dict:
    return {norm_key(k): v for k, v in (d or {}).items()}

def normalise_coverlevel_db_first(value: str, allow_fuzzy: bool, client_id: str | None):
    if client_id:
        try:
            vm = get_value_map_cover_level(client_id)
            if vm:
                mapped, method = normalise_value_with_map(value, _normalise_map_keys_local(vm), allow_fuzzy)
                if method != "none":
                    return mapped, f"client_db:{method}"
        except Exception:
            pass
    mapped, method = normalise_coverlevel(value, allow_fuzzy)
    return mapped, f"fallback:{method}"

def normalise_covertype_db_first(value: str, allow_fuzzy: bool, client_id: str | None):
    if client_id:
        try:
            vm = get_value_map_cover_type(client_id)
            if vm:
                mapped, method = normalise_value_with_map(value, _normalise_map_keys_local(vm), allow_fuzzy)
                if method != "none":
                    return mapped, f"client_db:{method}"
        except Exception:
            pass
    mapped, method = normalise_covertype(value, allow_fuzzy)
    return mapped, f"fallback:{method}"

## End Client Database Integration 09012026##


def safe_filename(s: str) -> str:
    s = clean_text(s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s)
    return s[:80] if s else "default"

def ensure_dir(p: str) -> str:
    os.makedirs(p, exist_ok=True)
    return p

def _iter_client_groups(std_all_obj):
    """
    Yield (client_id, client_name, rows_or_df) per client group.

    Supports:
      - list[dict] (rows)
      - dict (single row dict OR dict of groups)
      - pandas DataFrame (if ever used later)
      - list[DataFrame]
    """

    # --- helper: is this a pandas-like DataFrame?
    def _is_df(x):
        return hasattr(x, "columns") and hasattr(x, "copy")

    # If caller gave a dict, it might be:
    #  (a) a single row dict  OR
    #  (b) a dict of groups { (cid,cname): rows/df } or { cid: rows/df }
    if isinstance(std_all_obj, dict):
        # (a) single row dict
        if "Client ID" in std_all_obj or "Client Name" in std_all_obj:
            rows = [std_all_obj]
            std_all_obj = rows
        else:
            # (b) dict of groups
            for k, v in std_all_obj.items():
                if isinstance(k, tuple) and len(k) >= 2:
                    cid, cname = k[0], k[1]
                else:
                    cid, cname = k, "UNKNOWN"
                yield str(cid).strip(), str(cname).strip(), v
            return

    # Normalise into a list of "chunks"
    chunks = std_all_obj if isinstance(std_all_obj, list) else [std_all_obj]

    # If chunks are dict-rows, group them
    if chunks and isinstance(chunks[0], dict):
        grouped = {}
        for r in chunks:
            cid = str(r.get("Client ID", "")).strip()
            cname = str(r.get("Client Name", "")).strip()
            if not cid:
                cid = "UNKNOWN"
            if not cname:
                cname = "UNKNOWN"
            grouped.setdefault((cid, cname), []).append(r)

        for (cid, cname), rows in grouped.items():
            yield cid, cname, rows
        return

    # If chunks are DataFrames (future-proof)
    for df in chunks:
        if _is_df(df) and ("Client ID" in df.columns) and ("Client Name" in df.columns):
            tmp = df.copy()
            tmp["Client ID"] = tmp["Client ID"].astype(str).str.strip()
            tmp["Client Name"] = tmp["Client Name"].astype(str).str.strip()
            tmp = tmp[tmp["Client ID"] != ""]

            if tmp.empty:
                continue

            for (cid, cname), g in tmp.groupby(["Client ID", "Client Name"], dropna=False):
                yield str(cid).strip(), str(cname).strip(), g
        else:
            # Unknown structure: treat as one group
            yield "UNKNOWN", "UNKNOWN", df


def safe_filename_component(s: str) -> str:
    if s is None:
        return "UNKNOWN"
    s = clean_text(str(s)).strip()
    s = s.replace(".", "_")
    s = re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(". ")
    return s[:120] if s else "UNKNOWN"

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def parse_uk_date(d: str):
    d = clean_text(d or "").strip()
    if not d:
        return None
    d = d.replace(".", "/").replace("\\", "/")
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]
    for fmt in formats:
        try:
            return datetime.strptime(d, fmt)
        except Exception:
            pass
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2})$", d)
    if m:
        dd, mm, yy = m.groups()
        yy = int(yy)
        yy += 2000 if yy < 70 else 1900
        try:
            return datetime(yy, int(mm), int(dd))
        except Exception:
            return None
    return None

def is_number(x: str) -> bool:
    x = clean_text(x or "").strip()
    if not x:
        return True
    try:
        float(x)
        return True
    except Exception:
        return False

def fuzzy_match_key(target_norm: str, candidates: list[str], threshold: float):
    best_key = None
    best_score = 0.0
    for k in candidates:
        sc = similarity(target_norm, k)
        if sc > best_score:
            best_score = sc
            best_key = k
    if best_key and best_score >= threshold:
        return best_key
    return None

def normalise_value_with_map(raw_value: str, value_map: dict, allow_fuzzy: bool):
    raw_value = "" if raw_value is None else clean_text(str(raw_value))
    key = norm_key(raw_value)
    if not key:
        return "", "none"
    if key in value_map:
        return value_map[key], "direct"
    if allow_fuzzy:
        best = fuzzy_match_key(key, list(value_map.keys()), VALUE_FUZZY_THRESHOLD)
        if best:
            return value_map[best], "fuzzy"
    return raw_value.strip(), "none"

def safe_float(x: str):
    x = clean_text(x or "").strip()
    if x == "":
        return 0.0, True
    try:
        return float(x), True
    except Exception:
        return 0.0, False

def ensure_unique_path(path: str, safe_mode: bool):
    if not safe_mode:
        return path
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{root}_{stamp}{ext}"

def default_prev_month_yyyymm():
    today = datetime.today()
    first_of_this_month = today.replace(day=1)
    prev_month_last_day = first_of_this_month - timedelta(days=1)
    return prev_month_last_day.strftime("%Y-%m")

def valid_invoice_month(s):
    s = (s or "").strip()
    try:
        datetime.strptime(s, "%Y-%m")
        return True
    except Exception:
        return False
# -------------------------
# Inbox month helpers (v11.3)
# -------------------------
def infer_month_from_inbox_path(file_path: str) -> str | None:
    """
    If file lives in ...\\in\\Inbox\\YYYY-MM\\file.csv, return YYYY-MM.
    Otherwise return None (fallback to config/default).
    """
    try:
        p = Path(file_path)
        parent = p.parent.name  # e.g. "2025-12"
        return parent if valid_invoice_month(parent) else None
    except Exception:
        return None

def processed_dir_for_month(invoice_month: str) -> str:
    d = os.path.join(PROCESSED_DIR, invoice_month)
    os.makedirs(d, exist_ok=True)
    return d

def failed_dir_for_month(category: str, invoice_month: str) -> str:
    d = os.path.join(FAILED_DIR, category, invoice_month)
    os.makedirs(d, exist_ok=True)
    return d

def yyyymm_to_label(yyyymm: str) -> str:
    try:
        dt = datetime.strptime(yyyymm, "%Y-%m")
        return dt.strftime("%b-%y")
    except Exception:
        return yyyymm

def ensure_month_folder(out_root: str, invoice_month_yyyymm: str) -> str:
    folder = os.path.join(out_root, invoice_month_yyyymm)
    os.makedirs(folder, exist_ok=True)
    return folder

def ensure_month_subfolders(out_root: str, invoice_month_yyyymm: str) -> dict:
    root = ensure_month_folder(out_root, invoice_month_yyyymm)
    paths = {"root": root}
    for k, sub in SUBFOLDERS.items():
        p = os.path.join(root, sub)
        os.makedirs(p, exist_ok=True)
        paths[k] = p
    return paths

def clean_csv_filename(client_name: str, client_id: str, invoice_month_yyyymm: str) -> str:
    cn = safe_filename_component(client_name)
    cid = safe_filename_component(client_id)
    return f"{cn}.{cid}.{invoice_month_yyyymm} (Clean).csv"

def list_clean_csvs(clean_dir: str, target_month: str | None = None) -> list[str]:
    p = Path(clean_dir)
    if not p.exists():
        return []
    out = []
    for f in p.glob("*.csv"):
        m = CLEAN_NAME_RE.match(f.name)
        if not m:
            continue
        if target_month and m.group("month") != target_month:
            continue
        out.append(str(f))
    out.sort(key=lambda x: Path(x).name.lower())
    return out

def list_legacy_standardised_csvs(month_root_dir: str, target_month: str | None = None) -> list[str]:
    p = Path(month_root_dir)
    if not p.exists():
        return []
    out = []
    for f in p.glob("standardised.*.csv"):
        m = STANDARDISED_NAME_RE.match(f.name)
        if not m:
            continue
        if target_month and m.group("month") != target_month:
            continue
        out.append(str(f))
    out.sort(key=lambda x: Path(x).name.lower())
    return out

def validate_csv_header(csv_path: str, required_cols: list[str], delimiter: str) -> tuple[bool, str]:
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            first = f.readline()
            if first.lower().startswith("sep="):
                pass
            else:
                f.seek(0)
            reader = csv.reader(f, delimiter=delimiter, quotechar='"')
            header = next(reader, None)
            if not header:
                return False, "Empty file (no header)."
        header_set = {clean_text(h).strip() for h in header if h is not None}
        missing = [c for c in required_cols if c not in header_set]
        if missing:
            return False, "Missing required columns: " + ", ".join(missing)
        return True, ""
    except UnicodeDecodeError:
        return False, "Encoding issue reading header."
    except Exception as e:
        return False, f"Could not read header: {e}"

def try_save_workbook_with_lock_fallback(wb, target_path: str) -> str:
    try:
        wb.save(target_path)
        return target_path
    except PermissionError:
        base, ext = os.path.splitext(target_path)
        alt = f"{base}__ALT_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
        wb.save(alt)
        return alt


# -------------------------
# Workflow 2 filename helpers (v10.1)
# -------------------------
def wf2_client_identity_from_rows(std_rows: list[dict]) -> tuple[str, str]:
    names = sorted({
        clean_text((r.get("Client Name") or "")).strip()
        for r in std_rows
        if clean_text((r.get("Client Name") or "")).strip()
    })
    ids = sorted({
        clean_text((r.get("Client ID") or "")).strip()
        for r in std_rows
        if clean_text((r.get("Client ID") or "")).strip()
    })

    if len(names) == 1:
        client_name = names[0]
    elif len(names) == 0:
        client_name = "UNKNOWN_CLIENT"
    else:
        client_name = "(Multiple Clients)"

    if len(ids) == 1:
        client_id = ids[0]
    elif len(ids) == 0:
        client_id = "UNKNOWN"
    else:
        client_id = "MULTI"

    return client_name, client_id

def report_filename(client_name: str, client_id: str, invoice_month: str, report_label: str) -> str:
    cn = safe_filename_component(client_name)
    cid = safe_filename_component(client_id)
    return f"{cn}.{cid}.{invoice_month} ({report_label}).csv"

# -------------------------
# Excess + Claim Limit mapping
# -------------------------
EXCESS_OPTIONS = ["£50", "£75", "£100"]

CLAIM_LIMIT_BY_LEVEL_AND_EXCESS = {
    "Standard": {"£50": "£500",  "£75": "£1,000", "£100": "£1,500"},
    "Premier":  {"£50": "£1,000","£75": "£1,500", "£100": "£3,000"},
}

def claim_limit_for(coverlevel: str, excess: str) -> str:
    coverlevel = clean_text(coverlevel or "").strip()
    excess = clean_text(excess or "").strip()
    return CLAIM_LIMIT_BY_LEVEL_AND_EXCESS.get(coverlevel, {}).get(excess, "")

# -------------------------
# Field Synonyms
# -------------------------
SYNONYMS_TO_STANDARD = {
    "clientid": "Client ID",
    "clientname": "Client Name",

    "employeeuniqueid": "Uniqueid",
    "employeekey": "Uniqueid",
    "staffnumber": "Uniqueid",
    "employeenumber": "Uniqueid",
    "employeeid": "Uniqueid",

    "forename": "Firstname",
    "forenames": "Firstname",
    "firstname": "Firstname",
    "employeefirstname": "Firstname",

    "employeesurname": "Surname",
    "surname": "Surname",

    "address1": "Add1",
    "addressline1": "Add1",
    "homeaddressline1": "Add1",

    "address2": "Add2",
    "addressline2": "Add2",
    "homeaddressline2": "Add2",

    "address3": "Add3",
    "addressline3": "Add3",
    "homeaddressline3": "Add3",

    "town": "City",
    "city": "City",
    "address4": "City",
    "addressline4": "City",
    "homeaddress4": "City",
    "homeaddresscity": "City",
    "add4": "City",

    "county": "County",
    "homeaddress5": "County",
    "homeaddresscounty": "County",
    "addressline5": "County",

    "postcode": "Postcode",
    "pcode": "Postcode",
    "homeaddresspostcode": "Postcode",
    "postalcode": "Postcode",
    "homepostcode": "Postcode",

    "email": "Email",
    "emailaddress": "Email",
    "workemailaddress": "Email",

    "option": "CoverLevel",
    "plan": "CoverLevel",
    "levelofcover": "CoverLevel",
    "coveroption": "CoverLevel",
    "tiername": "CoverLevel",

    "option2": "CoverType",
    "covertype": "CoverType",
    "employeecategory": "CoverType",
    "coveragename": "CoverType",
    "whocovered": "CoverType",
    "itemoption": "CoverType",
    "itemname": "CoverType",

    "startofcover": "Start",
    "benefitstartdate": "Start",
    "coveragestartdate": "Start",
    "coverstartdate": "Start",
    "selectioneffectivedate": "Start",
    "applicationdate": "Start",

    "leavingdate": "End",
    "benefitenddate": "End",
    "selectionenddate": "End",
    "applicationenddate": "End",
    "leavedate": "End",

    "pcm": "pcm",
    "monthlyvalue": "pcm",
    "periodcost": "pcm",
    "monthlycost": "pcm",
    "employeemonthlypremium": "pcm",
    "monthlyemployeecost": "pcm",
    "premium": "pcm",
}

# -------------------------
# Value maps
# -------------------------
COVERLEVEL_VALUE_MAP = {
    "Gadget Insurance - Standard": "Standard",
    "Standard": "Standard",
    "Standard +": "Standard",
    "Standard Cover": "Standard",
    "Std": "Standard",

    "Gadget Insurance - Premier": "Premier",
    "Premier": "Premier",
    "Premier +": "Premier",
    "Premier Cover": "Premier",
    "Prm": "Premier",
    "Prem": "Premier",
}

COVERTYPE_VALUE_MAP = {
    "Employee Only": "Employee Only",
    "Employee": "Employee Only",
    "Single": "Employee Only",
    "Self": "Employee Only",
    "Self only": "Employee Only",
    "For you": "Employee Only",
    "sefl": "Employee Only",

    "Employee and Partner": "Employee and Partner",
    "Employee + Partner": "Employee and Partner",
    "Couple": "Employee and Partner",
    "Self & Partner": "Employee and Partner",
    "Self and Partner": "Employee and Partner",
    "For you and your partner": "Employee and Partner",
    "sefl & partner": "Employee and Partner",
    "sefl and partner": "Employee and Partner",

    "Employee and Family": "Employee and Family",
    "Employee + Family": "Employee and Family",
    "Family": "Employee and Family",
    "Self and Immediate Family": "Employee and Family",
    "Self & Immediate Family": "Employee and Family",
    "For you and your family": "Employee and Family",
    "sefl and immediate family": "Employee and Family",
}

COVERLEVEL_VALUE_MAP = normalise_map_keys(COVERLEVEL_VALUE_MAP)
COVERTYPE_VALUE_MAP = normalise_map_keys(COVERTYPE_VALUE_MAP)

def normalise_coverlevel(value: str, allow_fuzzy: bool):
    return normalise_value_with_map(value, COVERLEVEL_VALUE_MAP, allow_fuzzy)

def normalise_covertype(value: str, allow_fuzzy: bool):
    return normalise_value_with_map(value, COVERTYPE_VALUE_MAP, allow_fuzzy)

# -------------------------
# Auto-suggest headers
# -------------------------
def auto_suggest(client_fields, standard_fields, synonyms_to_standard=None, threshold=0.90):
    synonyms_to_standard = synonyms_to_standard or {}
    suggestions = {}
    for c in client_fields:
        if not c:
            continue
        compact = re.sub(r"[^a-z0-9]+", "", norm_key(c))
        if compact in synonyms_to_standard:
            suggestions[c] = synonyms_to_standard[compact]
            continue
        best_std, best_score = None, 0.0
        for s in standard_fields:
            score = SequenceMatcher(None, norm(c), norm(s)).ratio()
            if score > best_score:
                best_score = score
                best_std = s
        if best_std and best_score >= threshold:
            suggestions[c] = best_std
    return suggestions

# -------------------------
# CSV header detection + mixed reader
# -------------------------
def detect_delimiter_and_headers(path: str):
    candidates = [",", ";", "\t", "|"]

    def split(line, d):
        return next(csv.reader([line], delimiter=d, quotechar='"'))

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        header_line = None
        for line in f:
            line = line.strip("\r\n").lstrip("\ufeff")
            if not line.strip():
                continue
            if line.lower().startswith("sep="):
                continue
            header_line = line
            break

    if not header_line:
        return [], ","

    if len(header_line) >= 2 and header_line[0] == '"' and header_line[-1] == '"' and header_line[1:-1].count('"') == 0:
        header_line = header_line[1:-1]

    best_d = ","
    best_n = 1
    for d in candidates:
        parts = split(header_line, d)
        if len(parts) > best_n:
            best_n = len(parts)
            best_d = d

    headers = [clean_text(h.strip()) for h in split(header_line, best_d) if str(h).strip()]
    return headers, best_d

def _build_reader_with_unwrapped_header(input_csv_path: str, _delim_ignored: str):
    candidates = [",", ";", "\t", "|"]

    def split(line, d):
        return next(csv.reader([line], delimiter=d, quotechar='"'))

    lines = []
    with open(input_csv_path, "r", encoding="utf-8-sig", newline="") as f:
        for line in f:
            line = line.strip("\r\n").lstrip("\ufeff")
            if not line.strip():
                continue
            if line.lower().startswith("sep="):
                continue
            lines.append(line)

    if not lines:
        raise ValueError("CSV file is empty.")

    header_line = lines[0]
    if len(header_line) >= 2 and header_line[0] == '"' and header_line[-1] == '"' and header_line[1:-1].count('"') == 0:
        header_line = header_line[1:-1]

    data_line = None
    for ln in lines[1:]:
        if ln.strip():
            data_line = ln
            break

    header_delim = ","
    header_cols_n = 1
    for d in candidates:
        n = len(split(header_line, d))
        if n > header_cols_n:
            header_cols_n = n
            header_delim = d
    headers = [clean_text(h.strip()) for h in split(header_line, header_delim)]

    data_delim = header_delim
    if data_line:
        data_cols_n = 1
        for d in candidates:
            n = len(split(data_line, d))
            if n > data_cols_n:
                data_cols_n = n
                data_delim = d

    def row_dicts():
        reader = csv.reader(lines[1:], delimiter=data_delim, quotechar='"')
        for row in reader:
            if not row:
                continue
            if len(row) == 1:
                cell = row[0]
                if "," in cell:
                    row = split(cell, ",")
                elif "\t" in cell:
                    row = split(cell, "\t")
                elif ";" in cell:
                    row = split(cell, ";")
                elif "|" in cell:
                    row = split(cell, "|")

            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]

            out = {}
            for i in range(len(headers)):
                out[headers[i]] = clean_text(row[i])
            yield out

    class PseudoDictReader:
        def __init__(self, fieldnames, gen, header_delim, data_delim):
            self.fieldnames = fieldnames
            self._gen = gen
            self.header_delim = header_delim
            self.data_delim = data_delim
        def __iter__(self): return self
        def __next__(self): return next(self._gen)

    return PseudoDictReader(headers, row_dicts(), header_delim, data_delim)

def _std_to_client_from_mapping(reader_fieldnames, mapping: dict):
    mapping_norm = {norm_key(k): v for k, v in (mapping or {}).items()}
    std_to_client_actual = {}
    for actual_header in (reader_fieldnames or []):
        std = mapping_norm.get(norm_key(actual_header))
        if std and std not in std_to_client_actual:
            std_to_client_actual[std] = actual_header
    return std_to_client_actual

# -------------------------
# Mapping persistence
# -------------------------
def mapping_path_for_client(client_id: str | None):
    if not client_id:
        return os.path.join(MAPPINGS_DIR, "default_mapping.json")
    return os.path.join(MAPPINGS_DIR, f"{safe_filename(client_id)}_mapping.json")

def auto_save_mapping(mapping: dict, client_id: str | None):
    path = mapping_path_for_client(client_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        return path
    except Exception:
        return None

def auto_load_mapping_if_exists(client_id: str | None):
    candidates = []
    if client_id:
        candidates.append(mapping_path_for_client(client_id))
    candidates.append(os.path.join(MAPPINGS_DIR, "default_mapping.json"))

    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    return {str(k): str(v) for k, v in loaded.items()}, p
            except Exception:
                pass
    return None, None

# -------------------------
# Validation
# -------------------------
def validate_rows(input_csv_path: str, mapping: dict, detected_header_delim: str,
                  normalise_values: bool, strict_values: bool, allow_fuzzy_values: bool):
    reader = _build_reader_with_unwrapped_header(input_csv_path, detected_header_delim)
    std_to_client = _std_to_client_from_mapping(reader.fieldnames, mapping)

    uid_h = std_to_client.get("Uniqueid")
    start_h = std_to_client.get("Start")
    end_h = std_to_client.get("End")
    pcm_h = std_to_client.get("pcm")
    level_h = std_to_client.get("CoverLevel")
    type_h = std_to_client.get("CoverType")

    total = 0
    missing_uid = 0
    bad_start = 0
    bad_end = 0
    bad_pcm = 0
    missing_level = 0
    missing_type = 0

    unknown_coverlevel = {}
    unknown_covertype = {}

    fuzzy_fixed_level = 0
    fuzzy_fixed_type = 0

    examples = {
        "missing_uid": [], "bad_start": [], "bad_end": [], "bad_pcm": [],
        "missing_level": [], "missing_type": [],
        "unknown_coverlevel": [], "unknown_covertype": []
    }

    for row in reader:
        total += 1

        if uid_h:
            uid = (row.get(uid_h) or "").strip()
            if not uid:
                missing_uid += 1
                if len(examples["missing_uid"]) < 5:
                    examples["missing_uid"].append(f"Row {total}: Uniqueid blank")

        if start_h:
            s = (row.get(start_h) or "").strip()
            if s and not parse_uk_date(s):
                bad_start += 1
                if len(examples["bad_start"]) < 5:
                    examples["bad_start"].append(f"Row {total}: Start='{s}'")

        if end_h:
            e = (row.get(end_h) or "").strip()
            if e and not parse_uk_date(e):
                bad_end += 1
                if len(examples["bad_end"]) < 5:
                    examples["bad_end"].append(f"Row {total}: End='{e}'")

        if pcm_h:
            p = (row.get(pcm_h) or "").strip()
            if p and not is_number(p):
                bad_pcm += 1
                if len(examples["bad_pcm"]) < 5:
                    examples["bad_pcm"].append(f"Row {total}: pcm='{p}'")

        if level_h:
            raw = (row.get(level_h) or "").strip()
            if not raw:
                missing_level += 1
                if len(examples["missing_level"]) < 5:
                    examples["missing_level"].append(f"Row {total}: CoverLevel blank")
            else:
                if normalise_values:
                    mapped, method = normalise_coverlevel_db_first(raw, allow_fuzzy_values, resolved_client_id)
                    if method == "fuzzy":
                        fuzzy_fixed_level += 1
                    if mapped not in CANONICAL_COVERLEVEL:
                        unknown_coverlevel[raw] = unknown_coverlevel.get(raw, 0) + 1
                else:
                    if raw not in CANONICAL_COVERLEVEL:
                        unknown_coverlevel[raw] = unknown_coverlevel.get(raw, 0) + 1

        if type_h:
            raw = (row.get(type_h) or "").strip()
            if not raw:
                missing_type += 1
                if len(examples["missing_type"]) < 5:
                    examples["missing_type"].append(f"Row {total}: CoverType blank")
            else:
                if normalise_values:
                    mapped, method = normalise_covertype_db_first(raw, allow_fuzzy_values, resolved_client_id)
                    if method == "fuzzy":
                        fuzzy_fixed_type += 1
                    if mapped not in CANONICAL_COVERTYPE:
                        unknown_covertype[raw] = unknown_covertype.get(raw, 0) + 1
                else:
                    if raw not in CANONICAL_COVERTYPE:
                        unknown_covertype[raw] = unknown_covertype.get(raw, 0) + 1

    blocks_export = bool(strict_values and (unknown_coverlevel or unknown_covertype))

    return {
        "total": total,
        "missing_uid": missing_uid,
        "bad_start": bad_start,
        "bad_end": bad_end,
        "bad_pcm": bad_pcm,
        "missing_level": missing_level,
        "missing_type": missing_type,
        "unknown_coverlevel": unknown_coverlevel,
        "unknown_covertype": unknown_covertype,
        "fuzzy_fixed_level": fuzzy_fixed_level,
        "fuzzy_fixed_type": fuzzy_fixed_type,
        "examples": examples,
        "header_delim": getattr(reader, "header_delim", detected_header_delim),
        "data_delim": getattr(reader, "data_delim", "?"),
        "blocks_export": blocks_export,
    }

# -------------------------
# Exporters (Workflow 1)
# -------------------------
def export_to_csv(input_csv_path: str, output_csv_path: str, mapping: dict,
                  standard_fields: list[str], header_delim: str,
                  normalise_values: bool, allow_fuzzy_values: bool):
    reader = _build_reader_with_unwrapped_header(input_csv_path, header_delim)
    std_to_client_actual = _std_to_client_from_mapping(reader.fieldnames, mapping)
    if not std_to_client_actual:
        raise ValueError("No mapped columns were found for CSV export.")

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

    with open(output_csv_path, "w", encoding="utf-8-sig", newline="") as f_out:
        f_out.write(f"sep={CSV_OUTPUT_DELIMITER}\n")
        writer = csv.DictWriter(
            f_out,
            fieldnames=standard_fields,
            delimiter=CSV_OUTPUT_DELIMITER,
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        row_count = 0
        for row in reader:
            out_row = {}
            for std in standard_fields:
                client_key = std_to_client_actual.get(std)
                value = row.get(client_key, "") if client_key else ""
                if normalise_values and std == "CoverLevel":
                    value, _src = normalise_coverlevel_db_first(value, allow_fuzzy_values, resolved_client_id)
                if normalise_values and std == "CoverType":
                    value, _src = normalise_covertype_db_first(value, allow_fuzzy_values, resolved_client_id)
                out_row[std] = clean_text(value)
            writer.writerow(out_row)
            row_count += 1

    if row_count == 0:
        raise ValueError("No data rows were read from the CSV.")
    return output_csv_path

# -------------------------
# Workflow 2 (Invoicing)
# -------------------------
WF2_COL_CLIENT = "Client Name"
WF2_COL_COVERLEVEL = "CoverLevel"
WF2_COL_COVERTYPE = "CoverType"
WF2_COL_PCM = "pcm"

WF2_COVERLEVELS = ["Standard", "Premier"]
WF2_BUCKETS = ["Employee", "Employee & Partner", "Employee & Family"]

def wf2_coverlevel_normalise(x):
    k = norm_key(x)
    if k in ("standard", "standard cover", "std"):
        return "Standard", True
    if k in ("premier", "premier cover", "prm", "prem"):
        return "Premier", True
    if k == "":
        return "", False
    return clean_text((x or "").strip()), False

def wf2_covertype_to_bucket(x):
    k = norm_key(x).replace("sefl", "self")
    if k in ("employee only", "employee", "self", "single"):
        return "Employee", True
    if k in ("employee and partner", "employee + partner", "self & partner", "self and partner", "couple"):
        return "Employee & Partner", True
    if k in ("employee and family", "employee + family", "self and immediate family", "self & immediate family", "family"):
        return "Employee & Family", True
    if k == "":
        return "", False
    return clean_text((x or "").strip()), False

def wf2_microstep_permutations(rows):
    agg = {(cl, b): {"Members": 0, "GrossPremium": 0.0} for cl in WF2_COVERLEVELS for b in WF2_BUCKETS}
    exceptions = []

    for i, r in enumerate(rows, start=1):
        client = clean_text((r.get(WF2_COL_CLIENT) or "").strip())
        cl_raw = r.get(WF2_COL_COVERLEVEL, "")
        ct_raw = r.get(WF2_COL_COVERTYPE, "")
        pcm_raw = r.get(WF2_COL_PCM, "")

        cl, ok_cl = wf2_coverlevel_normalise(cl_raw)
        b, ok_b = wf2_covertype_to_bucket(ct_raw)
        gross, ok_gross = safe_float(pcm_raw)

        if not client:
            exceptions.append({"RowNo": i, "Issue": "Missing Client"})
            continue
        if not ok_cl or cl not in WF2_COVERLEVELS:
            exceptions.append({"RowNo": i, "Issue": f"Invalid CoverLevel: {clean_text(cl_raw)}"})
            continue
        if not ok_b or b not in WF2_BUCKETS:
            exceptions.append({"RowNo": i, "Issue": f"Missing/Invalid PricingBucket from CoverType: {clean_text(ct_raw)}"})
            continue
        if not ok_gross:
            exceptions.append({"RowNo": i, "Issue": f"Invalid PCM: {clean_text(pcm_raw)}"})
            continue

        agg[(cl, b)]["Members"] += 1
        agg[(cl, b)]["GrossPremium"] += gross

    return agg, exceptions

def wf2_build_outputs(rows, invoice_month, ipt_rate, excess_selected):
    agg, exceptions = wf2_microstep_permutations(rows)

    clients = sorted(set(clean_text((r.get(WF2_COL_CLIENT) or "").strip())
                         for r in rows if clean_text((r.get(WF2_COL_CLIENT) or "").strip())))
    client_label = clients[0] if len(clients) == 1 else "(Multiple Clients)"

    micro_rows = []
    for cl in WF2_COVERLEVELS:
        for b in WF2_BUCKETS:
            v = agg[(cl, b)]
            micro_rows.append({
                "Month": invoice_month,
                "CoverLevel": cl,
                "PricingBucket": b,
                "Members": str(v["Members"]),
                "GrossPremiumSum": f"{round(v['GrossPremium'], 2):.2f}",
            })

    invoicing_rows = []
    total_gross_all = 0.0
    total_ipt_all = 0.0
    total_invoice_all = 0.0

    for cl in WF2_COVERLEVELS:
        for b in WF2_BUCKETS:
            v = agg[(cl, b)]
            gross = round(v["GrossPremium"], 2)
            ipt = round(gross * ipt_rate, 2)
            total = round(gross + ipt, 2)
            invoicing_rows.append({
                "Month": invoice_month,
                "Client": client_label,
                "Excess": excess_selected,
                "CoverLevel": cl,
                "ClaimLimit": claim_limit_for(cl, excess_selected),
                "PricingBucket": b,
                "Members": str(v["Members"]),
                "GrossPremium": f"{gross:.2f}",
                "IPT": f"{ipt:.2f}",
                "TotalInvoice": f"{total:.2f}",
            })
            total_gross_all += gross
            total_ipt_all += ipt
            total_invoice_all += total

    backup_rows = []
    for i, r in enumerate(rows, start=1):
        client = clean_text((r.get(WF2_COL_CLIENT) or "").strip())
        cl_raw = r.get(WF2_COL_COVERLEVEL, "")
        ct_raw = r.get(WF2_COL_COVERTYPE, "")
        pcm_raw = r.get(WF2_COL_PCM, "")

        cl, _ = wf2_coverlevel_normalise(cl_raw)
        b, _ = wf2_covertype_to_bucket(ct_raw)
        gross, ok_gross = safe_float(pcm_raw)

        backup_rows.append({
            "Month": invoice_month,
            "RowNo": str(i),
            "Client": client,
            "Excess": excess_selected,
            "CoverLevel_raw": clean_text((cl_raw or "").strip()),
            "CoverLevel": cl,
            "ClaimLimit": claim_limit_for(cl, excess_selected),
            "CoverType_raw": clean_text((ct_raw or "").strip()),
            "PricingBucket": b,
            "PCM_raw": clean_text((pcm_raw or "").strip()),
            "GrossPremium": (f"{gross:.2f}" if ok_gross else ""),
        })

    control_rows = [{
        "Version": __version__,
        "InvoiceMonth": invoice_month,
        "Excess": excess_selected,
        "IPTRate": str(ipt_rate),
        "RowsIn": str(len(rows)),
        "DistinctClients": str(len(clients)),
        "TotalGrossPremium": f"{round(total_gross_all,2):.2f}",
        "TotalIPT": f"{round(total_ipt_all,2):.2f}",
        "TotalInvoice": f"{round(total_invoice_all,2):.2f}",
        "Exceptions": str(len(exceptions)),
    }]

    return micro_rows, invoicing_rows, backup_rows, exceptions, control_rows

def _read_text_with_encodings(path, encodings):
    last_err = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read(), enc
        except Exception as e:
            last_err = e
    raise last_err

def wf2_read_standardised_csv(path: str):
    text, _used_enc = _read_text_with_encodings(path, ["utf-8-sig", "utf-16", "utf-16-le", "cp1252"])

    lines = [ln.strip("\r\n") for ln in text.splitlines() if ln.strip("\r\n").strip() != ""]
    header_line = None
    start_idx = 0
    for idx, ln in enumerate(lines):
        if ln.lower().startswith("sep="):
            continue
        header_line = ln
        start_idx = idx
        break
    if not header_line:
        return []

    candidates = [",", ";", "\t", "|"]
    best = ","
    best_n = 1
    for d in candidates:
        parts = next(csv.reader([header_line], delimiter=d, quotechar='"'))
        if len(parts) > best_n:
            best_n = len(parts)
            best = d

    rows = []
    rebuilt = "\n".join(lines[start_idx:])
    reader = csv.DictReader(rebuilt.splitlines(), delimiter=best, quotechar='"')
    for r in reader:
        clean_row = {}
        for k, v in r.items():
            clean_row[clean_text(k)] = clean_text(v)
        rows.append(clean_row)
    return rows

def wf2_write_csv(path, rows, fieldnames, safe_mode: bool):
    path = ensure_unique_path(path, safe_mode)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(f"sep={CSV_OUTPUT_DELIMITER}\n")
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_OUTPUT_DELIMITER, quotechar='"', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            out = {k: clean_text(r.get(k, "")) for k in fieldnames}
            w.writerow(out)
    return path

# -------------------------
# Bordereau (monthly)
# -------------------------
def read_all_clean_in_month(paths: dict, invoice_month: str) -> tuple[list[dict], list[tuple[str, str]]]:
    skipped = []
    required_cols = ["Client Name", "CoverLevel", "CoverType"]

    clean_files = list_clean_csvs(paths["clean_csv"], target_month=invoice_month)
    input_files = clean_files

    if not input_files:
        legacy_files = list_legacy_standardised_csvs(paths["root"], target_month=invoice_month)
        input_files = legacy_files

    rows_all = []
    for fp in input_files:
        ok, msg = validate_csv_header(fp, required_cols, CSV_OUTPUT_DELIMITER)
        if not ok:
            skipped.append((os.path.basename(fp), msg))
            continue
        try:
            rows = wf2_read_standardised_csv(fp)
            rows_all.extend(rows)
        except Exception as e:
            skipped.append((os.path.basename(fp), f"Read failed: {e}"))
            continue

    return rows_all, skipped
## NEW MASTER BORDEREAU EXPORT FUNCTION SECTION 2.2##
BORDEREAU_COLUMNS = [
    "Month of Inception / Renewal",
    "Policy Holder",
    "Policy No",
    "Excess level",
    "Total No Beneficiaries",
    "Standard - Employee Only",
    "Standard - Employee & Partner",
    "Standard - Employee & Family",
    "Standard - Total",
    "Premier - Employee Only",
    "Premier - Employee & Partner",
]

MASTER_KEY_COLS = ["Month of Inception / Renewal", "Policy Holder", "Policy No", "Excess level"]

NUMERIC_SUM_COLS = [
    "Total No Beneficiaries",
    "Standard - Employee Only",
    "Standard - Employee & Partner",
    "Standard - Employee & Family",
    "Standard - Total",
    "Premier - Employee Only",
    "Premier - Employee & Partner",
]

def _safe_int(x):
    try:
        if x is None: return 0
        if isinstance(x, str) and x.strip() == "": return 0
        return int(float(str(x).replace(",", "").strip()))
    except Exception:
        return 0

def _get_or_create_master_ws(master_path: str, sheet_name: str = "MASTER"):
    if os.path.exists(master_path):
        wb = load_workbook(master_path)
        ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.create_sheet(sheet_name)
        # ensure headers exist
        if ws.max_row < 1 or ws.cell(row=1, column=1).value is None:
            ws.append(BORDEREAU_COLUMNS)
        return wb, ws
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(BORDEREAU_COLUMNS)
        return wb, ws

def _row_key_from_dict(d: dict):
    return tuple(str(d.get(k, "")).strip() for k in MASTER_KEY_COLS)

def _row_key_from_ws(ws, row_idx: int, header_to_col: dict):
    vals = []
    for k in MASTER_KEY_COLS:
        c = header_to_col[k]
        v = ws.cell(row=row_idx, column=c).value
        vals.append(str(v).strip() if v is not None else "")
    return tuple(vals)

def _dict_to_row_list(d: dict):
    return [d.get(col, "") for col in BORDEREAU_COLUMNS]

def upsert_master_client_row(master_path: str, client_rows: list[dict]):
    """
    client_rows: the bordereau rows for one client (often 1 row, sometimes multiple).
    We collapse to one master row per client by summing numeric columns.
    """
    if not client_rows:
        return master_path

    # Build a single master row dict
    base = dict(client_rows[0])  # start from first row
    for col in NUMERIC_SUM_COLS:
        base[col] = 0

    for r in client_rows:
        for col in NUMERIC_SUM_COLS:
            base[col] = _safe_int(base.get(col)) + _safe_int(r.get(col))

    # Ensure required columns exist in dict
    for col in BORDEREAU_COLUMNS:
        base.setdefault(col, "")

    wb, ws = _get_or_create_master_ws(master_path)

    # Map headers to columns
    header_to_col = {}
    for j in range(1, ws.max_column + 1):
        h = ws.cell(row=1, column=j).value
        if h:
            header_to_col[str(h).strip()] = j
    # If headers are missing or wrong, reset headers (safe)
    if any(h not in header_to_col for h in BORDEREAU_COLUMNS):
        ws.delete_rows(1, ws.max_row)
        ws.append(BORDEREAU_COLUMNS)
        header_to_col = {h: i+1 for i, h in enumerate(BORDEREAU_COLUMNS)}

    target_key = _row_key_from_dict(base)

    # Find existing row
    found_row = None
    for r_idx in range(2, ws.max_row + 1):
        if _row_key_from_ws(ws, r_idx, header_to_col) == target_key:
            found_row = r_idx
            break

    row_list = _dict_to_row_list(base)

    if found_row:
        # Update in place
        for c_idx, val in enumerate(row_list, start=1):
            ws.cell(row=found_row, column=c_idx).value = val
    else:
        ws.append(row_list)

    wb.save(master_path)
    return master_path


## END OF NEW MASTER BORDEREAU EXPORT FUNCTION SECTION 2.2##
def generate_bordereau_rows_from_standardised(std_rows: list[dict], month_label: str, excess_selected: str):
    def to_bord_bucket(x):
        k = norm_key(x).replace("sefl", "self")
        if k in ("employee only", "employee", "self", "single"):
            return "Employee Only"
        if k in ("employee and partner", "employee + partner", "self & partner", "self and partner", "couple"):
            return "Employee & Partner"
        if k in ("employee and family", "employee + family", "self and immediate family", "self & immediate family", "family"):
            return "Employee & Family"
        return ""

    agg = {}
    for r in std_rows:
        client_name = clean_text((r.get("Client Name") or "").strip())
        if not client_name:
            continue
        client_id = clean_text((r.get("Client ID") or "").strip())
        key = (client_id, client_name)

        cl, ok_cl = wf2_coverlevel_normalise(r.get("CoverLevel", ""))
        b = to_bord_bucket(r.get("CoverType", ""))

        if not ok_cl or cl not in ("Standard", "Premier"):
            continue
        if b not in ("Employee Only", "Employee & Partner", "Employee & Family"):
            continue

        agg.setdefault(key, {})
        agg[key][(cl, b)] = agg[key].get((cl, b), 0) + 1

    def sort_key(item):
        (cid, cname) = item
        return (cname.lower(), (cid or "").lower())

    out = []
    for (client_id, client_name) in sorted(agg.keys(), key=sort_key):
        s_emp = agg[(client_id, client_name)].get(("Standard", "Employee Only"), 0)
        s_par = agg[(client_id, client_name)].get(("Standard", "Employee & Partner"), 0)
        s_fam = agg[(client_id, client_name)].get(("Standard", "Employee & Family"), 0)
        s_tot = s_emp + s_par + s_fam

        p_emp = agg[(client_id, client_name)].get(("Premier", "Employee Only"), 0)
        p_par = agg[(client_id, client_name)].get(("Premier", "Employee & Partner"), 0)
        p_fam = agg[(client_id, client_name)].get(("Premier", "Employee & Family"), 0)
        p_tot = p_emp + p_par + p_fam

        out.append({
            "Month of Inception / Renewal": month_label,
            "Policy Holder": client_name,
            "Policy No": client_id,
            "Excess level": excess_selected,
            "Total No Beneficiaries": str(s_tot + p_tot),

            "Standard - Employee Only": str(s_emp),
            "Standard - Employee & Partner": str(s_par),
            "Standard - Employee & Family": str(s_fam),
            "Standard - Total": str(s_tot),

            "Premier - Employee Only": str(p_emp),
            "Premier - Employee & Partner": str(p_par),
            "Premier - Employee & Family": str(p_fam),
            "Premier - Total": str(p_tot),
        })
    return out

def export_bordereau_to_xlsx(bord_rows: list[dict], out_xlsx_path: str, safe_mode: bool):
    if not OPENPYXL_AVAILABLE:
        raise ImportError("Excel export requires 'openpyxl'.")

    headers = [
        "Month of Inception / Renewal",
        "Policy Holder",
        "Policy No",
        "Excess level",
        "Total No Beneficiaries",
        "Standard - Employee Only",
        "Standard - Employee & Partner",
        "Standard - Employee & Family",
        "Standard - Total",
        "Premier - Employee Only",
        "Premier - Employee & Partner",
        "Premier - Employee & Family",
        "Premier - Total",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Bordereau"

    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c).value = h

    r = 2
    for row in bord_rows:
        for c, h in enumerate(headers, start=1):
            ws.cell(row=r, column=c).value = clean_text(row.get(h, ""))
        r += 1

    ws.freeze_panes = "A2"

    for col_idx, h in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(h)
        for rr in range(2, r):
            v = ws.cell(row=rr, column=col_idx).value
            if v is not None:
                max_len = max(max_len, len(str(v)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)

    os.makedirs(os.path.dirname(out_xlsx_path), exist_ok=True)

    out_xlsx_path = ensure_unique_path(out_xlsx_path, safe_mode)
    final_path = try_save_workbook_with_lock_fallback(wb, out_xlsx_path)
    return final_path

# -------------------------
# v11.1 Inbox exceptions + failure packs
# -------------------------
class InboxError(Exception):
    category = "UnexpectedError"
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}

class MissingMappingError(InboxError):
    category = "MissingMapping"

class HeaderMismatch(InboxError):
    category = "HeaderMismatch"

class BadEncoding(InboxError):
    category = "BadEncoding"

class ValidationErrors(InboxError):
    category = "ValidationErrors"

class UnknownCoverValues(InboxError):
    category = "UnknownCoverValues"

def stamp_compact():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")

def ensure_inbox_dirs():
    for p in (INBOX_DIR, PROCESSED_DIR, FAILED_DIR):
        os.makedirs(p, exist_ok=True)
# -------------------------
# v11.2 Email notifications (optional)
# -------------------------
def _can_send_email(cfg: dict, to_list=None, cc_list=None) -> bool:
    effective_to = to_list if to_list is not None else (cfg.get("email_to") or [])
    effective_cc = cc_list if cc_list is not None else (cfg.get("email_cc") or [])
    return (
        bool(cfg.get("email_enabled"))
        and bool(cfg.get("smtp_host"))
        and bool(cfg.get("email_from"))
        and bool(effective_to or effective_cc)
    )

## V13.1 (09012026) Creating Headers and Body for Emails ##

# -------------------------
# Email templating helpers
# -------------------------
def _tick(ok: bool) -> str:
    return "✅" if ok else "❌"

def _nice_path(p: str) -> str:
    return clean_text(p or "").strip()

def _rel_to_base(p: str, base: str) -> str:
    p = _nice_path(p)
    base = _nice_path(base)
    if not p:
        return ""
    try:
        if base and os.path.commonpath([p, base]) == os.path.normpath(base):
            return os.path.relpath(p, base)
    except Exception:
        pass
    return p

def _folder_and_file(p: str) -> tuple[str, str]:
    p = _nice_path(p)
    if not p:
        return "", ""
    return os.path.dirname(p), os.path.basename(p)

def _format_output_lines(outputs: dict, out_base: str) -> list[str]:
    """
    Builds nicely spaced bullet lines showing folder + filename.
    Shows base once in the email body (caller does that).
    """
    lines = []

    # Clean CSV (WF1 output)
    clean_csv = outputs.get("clean_csv") if isinstance(outputs, dict) else None
    if clean_csv:
        rel = _rel_to_base(clean_csv, out_base)
        folder, fname = _folder_and_file(rel)
        lines.append(f"• {_tick(True)} Clean CSV")
        lines.append(f"  Folder: {folder}")
        lines.append(f"  File:   {fname}")
        lines.append("")

    # WF2 outputs (list of file paths)
    wf2_list = outputs.get("workflow2") if isinstance(outputs, dict) else None
    if wf2_list:
        lines.append(f"• {_tick(True)} Workflow 2 Outputs ({len(wf2_list)} files)")
        for p in wf2_list:
            rel = _rel_to_base(p, out_base)
            folder, fname = _folder_and_file(rel)
            lines.append(f"  - Folder: {folder}")
            lines.append(f"    File:   {fname}")
            lines.append("")
    else:
        # Don’t mark WF2 as failed if it’s simply disabled; keep neutral wording.
        lines.append(f"• {_tick(True)} Workflow 2 Outputs")
        lines.append("  (No WF2 files were written — WF2 may be disabled or no outputs selected.)")
        lines.append("")

    # Bordereau per-client outputs
    bord_clients = outputs.get("bordereau_clients") if isinstance(outputs, dict) else None
    if bord_clients:
        lines.append(f"• {_tick(True)} Bordereau (Per-Client) ({len(bord_clients)} files)")
        for p in bord_clients:
            rel = _rel_to_base(p, out_base)
            folder, fname = _folder_and_file(rel)
            lines.append(f"  - Folder: {folder}")
            lines.append(f"    File:   {fname}")
            lines.append("")
    else:
        lines.append(f"• {_tick(True)} Bordereau (Per-Client)")
        lines.append("  (No per-client bordereau files were written — bordereau may be disabled.)")
        lines.append("")

    # Bordereau master
    bord_master = outputs.get("bordereau_master") if isinstance(outputs, dict) else None
    if bord_master:
        rel = _rel_to_base(bord_master, out_base)
        folder, fname = _folder_and_file(rel)
        lines.append(f"• {_tick(True)} Bordereau (Master)")
        lines.append(f"  Folder: {folder}")
        lines.append(f"  File:   {fname}")
        lines.append("")
    else:
        lines.append(f"• {_tick(True)} Bordereau (Master)")
        lines.append("  (No master bordereau file was written — master export may be disabled.)")
        lines.append("")

    return lines

def _try_infer_client_name_from_csv_quick(path: str) -> str:
    """
    Best-effort: read first data row and look for a column that looks like Client Name.
    Falls back to UNKNOWN_CLIENT if not possible.
    """
    try:
        headers, delim, _enc = detect_headers_best_effort(path)
        if not headers:
            return "UNKNOWN_CLIENT"

        # Find a likely "Client Name" header
        candidates = []
        for h in headers:
            hk = norm_key(h)
            if hk in ("client name", "clientname", "company", "employer", "organisation", "organization"):
                candidates.append(h)
        # If not found, try says "client" and "name" in header
        if not candidates:
            for h in headers:
                hk = norm_key(h)
                if ("client" in hk) and ("name" in hk):
                    candidates.append(h)

        if not candidates:
            return "UNKNOWN_CLIENT"

        reader = _build_reader_with_unwrapped_header(path, delim)
        first = next(iter(reader), None)
        if not first:
            return "UNKNOWN_CLIENT"

        for h in candidates:
            v = clean_text(first.get(h, "")).strip()
            if v:
                return v

        return "UNKNOWN_CLIENT"
    except Exception:
        return "UNKNOWN_CLIENT"

def build_success_email(client_name: str, filename: str, invoice_month: str, outputs: dict, out_base: str) -> tuple[str, str]:
    client_name = clean_text(client_name or "").strip() or "UNKNOWN_CLIENT"
    filename = clean_text(filename or "").strip()

    subject = f"Success: {client_name}"

    lines = []
    lines.append("✅ Gadget Processing Update")
    lines.append("")
    lines.append(f"Client: {client_name}")
    lines.append(f"File:   {filename}")
    if invoice_month:
        lines.append(f"Month:  {invoice_month}")
    lines.append(f"Version: v{__version__}")
    lines.append("")
    lines.append(f"Output base path:")
    lines.append(f"{out_base}")
    lines.append("")
    lines.append("Results:")
    lines.append("")

    # Process steps (always OK if we got here)
    lines.append(f"• {_tick(True)} Processed")
    lines.append("")

    # Output sections
    lines.extend(_format_output_lines(outputs or {}, out_base))

    # Trim trailing blank lines
    while lines and lines[-1] == "":
        lines.pop()

    body = "\n".join(lines)
    return subject, body

def build_failure_email(client_name: str, filename: str, invoice_month: str, category: str, reason: str, failure_pack: str) -> tuple[str, str]:
    client_name = clean_text(client_name or "").strip() or "UNKNOWN_CLIENT"
    filename = clean_text(filename or "").strip()
    category = clean_text(category or "").strip()
    reason = clean_text(reason or "").strip()
    failure_pack = clean_text(failure_pack or "").strip()

    subject = f"Failure: {client_name}"

    lines = []
    lines.append("❌ Gadget Processing Update")
    lines.append("")
    lines.append(f"Client: {client_name}")
    lines.append(f"File:   {filename}")
    if invoice_month:
        lines.append(f"Month:  {invoice_month}")
    lines.append(f"Version: v{__version__}")
    lines.append("")
    lines.append("Results:")
    lines.append("")
    lines.append(f"• {_tick(False)} Processed")
    lines.append("")
    lines.append(f"• {_tick(False)} Failure Category")
    lines.append(f"  {category}")
    lines.append("")
    lines.append(f"• {_tick(False)} Reason")
    lines.append(f"  {reason}")
    lines.append("")
    lines.append(f"• {_tick(False)} Failure Pack")
    lines.append(f"  {failure_pack}")
    lines.append("")
    lines.append("Next steps:")
    lines.append("• Open failure_summary.txt and failure_details.json in the pack")
    lines.append("• Fix the issue (mapping / values / encoding / data)")
    lines.append("• Re-run using --retry when ready")

    body = "\n".join(lines)
    return subject, body

## V13 Email Epic: Emails & Notifications Start##

def send_email(cfg: dict, subject: str, body: str, *, to_list=None, cc_list=None):
    to_final = to_list if (to_list is not None) else (cfg.get("email_to") or [])
    cc_final = cc_list if (cc_list is not None) else (cfg.get("email_cc") or [])
    if not _can_send_email(cfg, to_final, cc_final):
        print("[EMAIL] Skipped (disabled/incomplete config)")
        print(f"        enabled={cfg.get('email_enabled')}")
        print(f"        smtp_host={cfg.get('smtp_host')}")
        print(f"        email_from={cfg.get('email_from')}")
        print(f"        email_to={to_final}")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    
    # Use verified sender identity (SendGrid requirement)
    email_from = (cfg.get("email_from") or "").strip()
    if not email_from:
        raise ValueError("email_from is blank in config")
  
    # Guardrail: prevent DMARC misalignment with Gmail From
    if email_from.lower().endswith("@gmail.com") or email_from.lower().endswith("@googlemail.com"):
        raise ValueError("Do not use Gmail addresses in email_from when sending via SendGrid. Use your authenticated domain.")


    sender = email_from
    msg["From"] = sender
    msg["Reply-To"] = email_from




    ## Correcting GMAIL ERROR by adding From header 13.1 09012026 ##

    msg["To"] = ", ".join([str(x) for x in to_final])

    cc_list = [str(x) for x in cc_final]

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    msg.set_content(body)

    recipients = []
    recipients.extend([str(x) for x in to_final])
    recipients.extend([str(x) for x in cc_final])

    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port", 587))
    use_tls = bool(cfg.get("smtp_tls", True))
    user = cfg.get("smtp_user") or ""
    pwd = cfg.get("smtp_pass") or ""

    print(f"[EMAIL] Attempting: host={host}:{port} from={msg['From']} to={msg['To']} cc={msg.get('Cc','')}")

    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.ehlo()
            if use_tls:
                s.starttls()
                s.ehlo()
            if user:
                s.login(user, pwd)
            s.sendmail(sender, recipients, msg.as_string())


        print(f"[EMAIL] Sent: {subject}")

    except Exception as e:
        print(f"[EMAIL WARN] Failed to send email: {type(e).__name__}: {e}")

def _event_enabled(cfg: dict, event_name: str) -> bool:
    if not cfg.get("email_enabled"):
        return False
    allowed = cfg.get("email_events") or []
    allowed = [str(x).strip().lower() for x in allowed]
    return (event_name or "").lower() in allowed

def notify_event(cfg: dict, event_name: str, filename: str, invoice_month: str,
                 details: dict | None = None, subject_extra: str = ""):
    if not _event_enabled(cfg, event_name):
        return

    prefix = (cfg.get("email_subject_prefix") or "Gadget").strip()
    event_label = event_name.upper()

    subject = f"{prefix} {event_label}: {filename}"
    if subject_extra:
        subject += f" | {subject_extra}"

    lines = [
        f"Event: {event_name}",
        f"File: {filename}",
        f"Month: {invoice_month}",
        "",
    ]

    details = details or {}
    if details:
        lines.append("Details:")
        for k in sorted(details.keys()):
            lines.append(f"- {k}: {details[k]}")
        lines.append("")

    send_email(cfg, subject, "\n".join(lines))
    print(f"[EMAIL] Queued: event={event_name} subject={subject}")



## V13 Email Epic: Emails & Notifications End##

# -------------------------
# v11.2 Config validation + startup banner
# -------------------------
_CFG_SCHEMA = {
    "invoice_month": ("str", ""),
    "normalise_values": ("bool", True),
    "allow_fuzzy_values": ("bool", True),
    "strict_values": ("bool", True),
    "safe_mode": ("bool", True),

    "run_workflow2": ("bool", True),
    "wf2_micro": ("bool", True),
    "wf2_invoice": ("bool", True),
    "wf2_backup": ("bool", True),
    "wf2_exceptions": ("bool", True),
    "wf2_control": ("bool", True),

    "ipt_rate": ("float", 0.12),
    "excess": ("str", "£50"),

    "run_bordereau": ("bool", True),

    "auto_suggest_threshold": ("float", 0.90),

    # Email (v11.2)
    "email_enabled": ("bool", False),
    "email_to": ("list", []),
    "email_from": ("str", ""),
    "smtp_host": ("str", ""),
    "smtp_port": ("int", 587),
    "smtp_tls": ("bool", True),
    "smtp_user": ("str", ""),
    "smtp_pass": ("str", ""),
##V13 Email Epic: Emails & Notifications Start##

    "email_events": ("list", ["failure", "success"]),   # allowed: ingestion,wf1,wf2,bordereau,success,failure
    "email_subject_prefix": ("str", "Gadget"),
    "email_cc": ("list", []),

##V13 Email Epic: Emails & Notifications End##
}

def _coerce_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    if isinstance(v, (int, float)):
        return bool(v)
    return False

def validate_and_normalise_config(raw: dict) -> tuple[dict, list[str], list[str]]:
    warnings, errors = [], []
    raw = raw or {}

    unknown = sorted([k for k in raw.keys() if k not in _CFG_SCHEMA])
    if unknown:
        warnings.append("Unknown config keys ignored: " + ", ".join(unknown))

    cfg = {}
    for k, (typ, default) in _CFG_SCHEMA.items():
        if k not in raw:
            cfg[k] = default
            continue
        v = raw.get(k)
        try:
            if typ == "bool":
                cfg[k] = _coerce_bool(v)
            elif typ == "str":
                cfg[k] = "" if v is None else str(v)
            elif typ == "int":
                cfg[k] = int(v)
            elif typ == "float":
                cfg[k] = float(v)
            elif typ == "list":
                if isinstance(v, list):
                    cfg[k] = v
                elif v is None or v == "":
                    cfg[k] = []
                else:
                    cfg[k] = [str(v)]
            else:
                cfg[k] = v
        except Exception:
            errors.append(f"Invalid value for '{k}' (expected {typ}): {v}")

    if cfg["invoice_month"] and not valid_invoice_month(cfg["invoice_month"]):
        errors.append(f"Invalid 'invoice_month': {cfg['invoice_month']} (expected YYYY-MM)")
    if cfg["excess"] and cfg["excess"] not in EXCESS_OPTIONS:
        errors.append(f"Invalid 'excess': {cfg['excess']} (expected one of {EXCESS_OPTIONS})")
    try:
        ipt = float(cfg.get("ipt_rate", 0.12))
        if not (0.0 <= ipt <= 1.0):
            warnings.append(f"ipt_rate looks unusual: {ipt} (expected 0.0–1.0)")
    except Exception:
        errors.append(f"Invalid 'ipt_rate': {cfg.get('ipt_rate')} (expected number)")

    if cfg["email_enabled"]:
        must = ["smtp_host", "smtp_port", "email_from"]
        missing = [m for m in must if not cfg.get(m)]
        if missing:
            errors.append("email_enabled is true but missing: " + ", ".join(missing))
        if not cfg.get("email_to"):
            errors.append("email_enabled is true but email_to is empty")

    return cfg, warnings, errors

def print_startup_banner(mode: str, cfg: dict, invoice_month: str):
    print(f"[v{__version__}] Mode={mode}")
    print(f"  BASE_DIR   : {BASE_DIR}")
    print(f"  INBOX_DIR  : {INBOX_DIR}")
    print(f"  OUT_DIR    : {OUT_DIR_DEFAULT}")
    print(f"  Month      : {invoice_month}")
    print(f"  WF2        : {bool(cfg.get('run_workflow2'))}")
    print(f"  Bordereau  : {bool(cfg.get('run_bordereau'))}")
    print(f"  SafeMode   : {bool(cfg.get('safe_mode'))}")
    print(f"  Email      : {bool(cfg.get('email_enabled'))}")

# -------------------------
# v11.2 Smart retry
# -------------------------
def _pack_original_csv(pack_dir: str) -> str | None:
    p = Path(pack_dir)
    if not p.exists() or not p.is_dir():
        return None
    for f in sorted(p.iterdir(), key=lambda x: x.name.lower()):
        if f.is_file() and f.suffix.lower() in ALLOWED_INBOX_EXTS:
            return str(f)
    return None

def _append_retry_history(pack_dir: str, entry: dict):
    path = os.path.join(pack_dir, "retry_history.jsonl")
    entry = dict(entry)
    entry["ts"] = datetime.now().isoformat(timespec="seconds")
    entry["version"] = __version__
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _write_retry_last(pack_dir: str, payload: dict):
    path = os.path.join(pack_dir, "retry_last_result.json")
    payload = dict(payload)
    payload["ts"] = datetime.now().isoformat(timespec="seconds")
    payload["version"] = __version__
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

def retry_failed_packs(cfg: dict, category: str | None, client_hint: str | None, dry_run: bool = False) -> dict:
    base = Path(FAILED_DIR)
    if not base.exists():
        return {"retried": 0, "ok": 0, "failed": 0, "skipped": 0}

    if category:
        cat_dirs = [base / category]
    else:
        cat_dirs = [p for p in base.iterdir() if p.is_dir()]

    def matches_hint(pack_path: str, orig_path: str, hint: str | None) -> bool:
        if not hint:
            return True
        h = hint.strip().lower()
        return (h in os.path.basename(pack_path).lower()) or (h in os.path.basename(orig_path).lower())

    summary = {"retried": 0, "ok": 0, "failed": 0, "skipped": 0}

    for cat in cat_dirs:
        if not cat.exists():
            continue

        for pack in sorted(cat.iterdir(), key=lambda p: p.name.lower()):
            if not pack.is_dir():
                continue

            orig = _pack_original_csv(str(pack))
            if not orig:
                summary["skipped"] += 1
                continue

            if not matches_hint(str(pack), orig, client_hint):
                summary["skipped"] += 1
                continue

            summary["retried"] += 1

            tmp_name = f"RETRY__{stamp_compact()}__{Path(orig).name}"
            tmp_path = os.path.join(RETRY_TMP_DIR, tmp_name)

            if dry_run:
                print(f"[DRY RUN] Would retry: {orig} (pack={pack})")
                continue

            shutil.copy2(orig, tmp_path)

            try:
                global read_inbox_config
                original_reader = read_inbox_config
                read_inbox_config = lambda: cfg

                result = process_single_inbox_file(tmp_path)

                read_inbox_config = original_reader

                _append_retry_history(str(pack), {"status": "ok", "outputs": result.get("outputs", {})})
                _write_retry_last(str(pack), {"status": "ok", "result": result})
                summary["ok"] += 1

            except Exception as e:
                try:
                    read_inbox_config = original_reader
                except Exception:
                    pass

                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

                _append_retry_history(str(pack), {"status": "failed", "message": str(e), "type": type(e).__name__})
                _write_retry_last(str(pack), {"status": "failed", "message": str(e), "type": type(e).__name__})
                summary["failed"] += 1

    return summary


def read_inbox_config() -> dict:
    """
    Optional config at C:\\GadgetClient\\in\\inbox_config.json
    """
    if not os.path.exists(INBOX_CONFIG_PATH):
        return {}
    try:
        with open(INBOX_CONFIG_PATH, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def detect_headers_best_effort(path: str):
    """
    Returns (headers, detected_delim, encoding_used).
    Tries common encodings including UTF-16.
    """
    try:
        text, enc = _read_text_with_encodings(path, ["utf-8-sig", "utf-16", "utf-16-le", "cp1252"])
    except Exception as e:
        raise BadEncoding(f"Could not read file with common encodings: {e}")

    lines = [ln.strip("\r\n") for ln in text.splitlines()]
    header_line = None
    for ln in lines:
        if not ln.strip():
            continue
        if ln.lower().startswith("sep="):
            continue
        header_line = ln.lstrip("\ufeff")
        break

    if not header_line:
        return [], ",", enc

    if len(header_line) >= 2 and header_line[0] == '"' and header_line[-1] == '"' and header_line[1:-1].count('"') == 0:
        header_line = header_line[1:-1]

    candidates = [",", ";", "\t", "|"]
    best_d = ","
    best_n = 1
    for d in candidates:
        parts = next(csv.reader([header_line], delimiter=d, quotechar='"'))
        if len(parts) > best_n:
            best_n = len(parts)
            best_d = d

    headers = [clean_text(h.strip()) for h in next(csv.reader([header_line], delimiter=best_d, quotechar='"')) if str(h).strip()]
    return headers, best_d, enc

def mapping_covers_required_fields(mapping: dict) -> tuple[bool, list[str]]:
    """
    Minimum to run WF1 + WF2 reliably.
    """
    required = ["Client ID", "Client Name", "Uniqueid", "CoverLevel", "CoverType", "pcm"]
    mapped_std = set(mapping.values())
    missing = [s for s in required if s not in mapped_std]
    return (len(missing) == 0), missing

def infer_client_identity_from_file(input_csv_path: str, mapping: dict, detected_header_delim: str) -> tuple[str, str]:
    """
    Reads first data row to infer Client Name/Client ID for filenames.
    """
    reader_probe = _build_reader_with_unwrapped_header(input_csv_path, detected_header_delim)
    std_to_client = _std_to_client_from_mapping(reader_probe.fieldnames, mapping)
    cid_h = std_to_client.get("Client ID")
    cname_h = std_to_client.get("Client Name")
    first_row = next(iter(reader_probe), {})
    cid = (first_row.get(cid_h) or "UNKNOWN").strip() if cid_h else "UNKNOWN"
    cname = (first_row.get(cname_h) or "UNKNOWN_CLIENT").strip() if cname_h else "UNKNOWN_CLIENT"
    return cname or "UNKNOWN_CLIENT", cid or "UNKNOWN"

def move_to_processed(original_path: str, invoice_month: str) -> str:
    base = os.path.basename(original_path)
    dest_dir = processed_dir_for_month(invoice_month)
    dest = os.path.join(dest_dir, f"{stamp_compact()}__{base}")
    shutil.move(original_path, dest)
    return dest

def build_failure_pack(category: str, original_filename: str, invoice_month: str) -> str:
    cat_month_dir = failed_dir_for_month(category, invoice_month)
    pack_dir = os.path.join(cat_month_dir, f"{stamp_compact()}__{original_filename}")
    os.makedirs(pack_dir, exist_ok=True)
    return pack_dir

def write_failure_pack(pack_dir: str, original_src_path: str, err: InboxError,
                       detected_headers: list[str], mapping_used: dict):
    """
    Moves original into pack, then writes summary/details.
    """
    original_filename = os.path.basename(original_src_path)
    original_dest = os.path.join(pack_dir, original_filename)
    shutil.move(original_src_path, original_dest)

    summary_path = os.path.join(pack_dir, "failure_summary.txt")
    details_path = os.path.join(pack_dir, "failure_details.json")
    headers_path = os.path.join(pack_dir, "detected_headers.txt")
    mapping_path = os.path.join(pack_dir, "mapping_used.json")

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"Category: {err.category}\n")
        f.write(f"Message: {clean_text(str(err))}\n")
        if err.details:
            f.write("\nDetails (high level):\n")
            for k in sorted(err.details.keys()):
                f.write(f"- {k}\n")

    payload = {
        "version": __version__,
        "category": err.category,
        "message": clean_text(str(err)),
        "details": err.details,
        "traceback": traceback.format_exc(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    with open(headers_path, "w", encoding="utf-8") as f:
        f.write("\n".join([clean_text(h) for h in (detected_headers or [])]))

    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping_used or {}, f, indent=2, ensure_ascii=False)

# -------------------------
# v11.1 Inbox processing (WF1 + optional WF2 + optional Bordereau)
# -------------------------
def process_single_inbox_file(input_csv_path: str, invoice_month_override: str | None = None) -> dict:
    fn = os.path.basename(input_csv_path)
    ext = os.path.splitext(fn)[1].lower()
    if ext not in ALLOWED_INBOX_EXTS:
        raise ValidationErrors(f"Unsupported file type '{ext}' in inbox (CSV only).")

    cfg = read_inbox_config()
    print("[CONFIG] Loaded email_from =", cfg.get("email_from"))
    # Month selection for headless export:
    invoice_month = (invoice_month_override or "").strip()
    if not valid_invoice_month(invoice_month):
        invoice_month = (cfg.get("invoice_month") or "").strip()
    if not valid_invoice_month(invoice_month):
        invoice_month = default_prev_month_yyyymm()

    normalise_values = bool(cfg.get("normalise_values", True))
    allow_fuzzy_values = bool(cfg.get("allow_fuzzy_values", True))
    strict_values = bool(cfg.get("strict_values", True))
    safe_mode = bool(cfg.get("safe_mode", True))

    # WF2 controls
    run_wf2 = bool(cfg.get("run_workflow2", True))
    wf2_micro_on = bool(cfg.get("wf2_micro", True))
    wf2_invoice_on = bool(cfg.get("wf2_invoice", True))
    wf2_backup_on = bool(cfg.get("wf2_backup", True))
    wf2_exceptions_on = bool(cfg.get("wf2_exceptions", True))
    wf2_control_on = bool(cfg.get("wf2_control", True))

    ipt_rate = cfg.get("ipt_rate", 0.12)
    try:
        ipt_rate = float(ipt_rate)
    except Exception:
        raise ValidationErrors(f"Invalid ipt_rate in inbox_config.json: {ipt_rate}")

    excess_selected = clean_text(cfg.get("excess", "£50")).strip()
    if excess_selected not in EXCESS_OPTIONS:
        raise ValidationErrors(
            f"Invalid excess in inbox_config.json: {excess_selected} (expected one of {EXCESS_OPTIONS})"
        )

    # WF3 (bordereau)
    run_bordereau = bool(cfg.get("run_bordereau", True))

    headers, detected_delim, enc_used = detect_headers_best_effort(input_csv_path)

##Start Client Database Integration 09012026##

    # Keep a module-level resolved_client_id so validate/export helpers can use it
    # (minimal change to keep v13 behaviour stable)
    global resolved_client_id, resolved_client_name
    resolved_client_id = None
    resolved_client_name = None
    res = None

    # 1) Build initial mapping from headers (synonyms + autosuggest)
    thresh = float(cfg.get("auto_suggest_threshold", 0.90))
    mapping = {}

    # 2) Infer a tentative client_id from first row IF we have enough mappings
    inferred_client_id = None
    try:
        # Use a light autosuggest first so we can potentially read Client ID / Name
        suggestions_probe = auto_suggest(headers, STANDARD_FIELDS, SYNONYMS_TO_STANDARD, threshold=thresh)
        for c, s in suggestions_probe.items():
            mapping[c] = s

        ok_min, _missing_std = mapping_covers_required_fields(mapping)
        if ok_min:
            _cname_tmp, cid_tmp = infer_client_identity_from_file(input_csv_path, mapping, detected_delim)
            inferred_client_id = cid_tmp if cid_tmp and cid_tmp != "UNKNOWN" else None
    except Exception:
        inferred_client_id = None

    # 3) Resolve via DB (safe overlay) using filename + inferred id (if any)
    try:
        res = resolve_client_identity(
            spreadsheet_client_name=None,
            inferred_client_name=None,
            filename=fn,
            inferred_client_id=inferred_client_id,
            allow_fuzzy=True
        )
        resolved_client_id = (res.client_id if (res and res.found and res.client_id) else None)
        resolved_client_name = (res.client_name if (res and res.found and res.client_name) else None)
    except Exception:
        res = None

    ##End Client Database Identity Resolution##

    thresh = float(cfg.get("auto_suggest_threshold", 0.90))
    mapping = {}

    # v15: DB template_fields overrides first
    template_fields = None
    applied_tf = {}
    if resolved_client_id:
        try:
            template_fields = get_template_fields(resolved_client_id)
            mapping, _n, applied_tf = apply_template_fields_overrides(headers, mapping, template_fields)
        except Exception:
            template_fields = None
            applied_tf = {}

    db_template_mapping = dict(mapping)

    # Existing v13/v14 logic next (synonyms + autosuggest)
    suggestions = auto_suggest(headers, STANDARD_FIELDS, SYNONYMS_TO_STANDARD, threshold=thresh)
    for c, s in suggestions.items():
        # Don't overwrite explicit DB template mapping if already set
        if c not in mapping:
            mapping[c] = s

    inferred_client_id = None
    try:
        ok_min, _missing_std = mapping_covers_required_fields(mapping)
        if ok_min:
            _cname_tmp, cid_tmp = infer_client_identity_from_file(input_csv_path, mapping, detected_delim)
            inferred_client_id = cid_tmp if cid_tmp and cid_tmp != "UNKNOWN" else None
    except Exception:
        inferred_client_id = None

    loaded_mapping, loaded_path = auto_load_mapping_if_exists(resolved_client_id or inferred_client_id)

    mapping_used = {
        "auto_suggest_threshold": thresh,
        "encoding_used_for_header_detect": enc_used,
        "loaded_mapping_path": loaded_path or "",
        "inferred_client_id": inferred_client_id or "",
        "normalise_values": normalise_values,
        "allow_fuzzy_values": allow_fuzzy_values,
        "strict_values": strict_values,
        "safe_mode": safe_mode,
        "run_workflow2": run_wf2,
        "run_bordereau": run_bordereau,
        "ipt_rate": ipt_rate,
        "excess": excess_selected,

        # Client DB overlay info
        "client_db_found": bool(res and res.found),
        "client_db_client_id": resolved_client_id or "",
        "client_db_client_name": resolved_client_name or "",
        "client_db_template_fields_applied_n": len(applied_tf),
        "client_db_template_fields_applied": applied_tf,
    }


    if loaded_mapping:
        # Priority: client database mappings > saved per-client mapping > auto-suggestions.
        merged_mapping = dict(suggestions)
        merged_mapping.update(loaded_mapping)
        merged_mapping.update(db_template_mapping)
        mapping = merged_mapping
        mapping_used["mapping_source"] = "client_db+saved" if db_template_mapping else "saved"
    else:
        mapping_used["mapping_source"] = "client_db+auto_suggest" if db_template_mapping else "auto_suggest"

    ok_min, missing_std = mapping_covers_required_fields(mapping)
    if not ok_min:
        raise MissingMappingError(
            f"Missing required mappings: {', '.join(missing_std)}",
            details={"missing_standard_fields": missing_std}
        )

    results = validate_rows(
        input_csv_path, mapping, detected_delim,
        normalise_values=normalise_values,
        strict_values=strict_values,
        allow_fuzzy_values=allow_fuzzy_values
    )

    if strict_values and results.get("blocks_export"):
        raise UnknownCoverValues(
            "Strict value rules: unknown CoverLevel/CoverType values found; export blocked.",
            details={
                "unknown_coverlevel": results.get("unknown_coverlevel", {}),
                "unknown_covertype": results.get("unknown_covertype", {}),
                "examples": results.get("examples", {}),
            }
        )

    client_name, client_id = infer_client_identity_from_file(input_csv_path, mapping, detected_delim)

    paths = ensure_month_subfolders(OUT_DIR_DEFAULT, invoice_month)

    # WF1
    out_name = clean_csv_filename(client_name, client_id, invoice_month)
    out_path = os.path.join(paths["clean_csv"], out_name)
    out_path = ensure_unique_path(out_path, safe_mode)

    saved_clean = export_to_csv(
        input_csv_path, out_path, mapping, STANDARD_FIELDS,
        detected_delim,
        normalise_values=normalise_values,
        allow_fuzzy_values=allow_fuzzy_values
    )

    saved_map_path = auto_save_mapping(
        mapping,
        client_id if client_id and client_id != "UNKNOWN" else inferred_client_id
    )
    mapping_used["saved_mapping_path"] = saved_map_path or ""
    mapping_used["mapping"] = dict(mapping)

    outputs = {"clean_csv": saved_clean}
    written_wf2 = []

    # v15 MappingAudit
    audit = {
        "version": __version__,
        "file": fn,
        "invoice_month": invoice_month,
        "client_resolution": (res.__dict__ if res else {}),
        "template_fields_applied": applied_tf,
        "mapping_source": mapping_used.get("mapping_source"),
    }

    audit_dir = os.path.join(paths["root"], "audit")
    os.makedirs(audit_dir, exist_ok=True)
    audit_path = os.path.join(
        audit_dir,
        f"MappingAudit.{safe_filename_component(client_name)}.{safe_filename_component(client_id)}.{invoice_month}.json"
    )
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    outputs["mapping_audit"] = audit_path

    # WF2
    if run_wf2:
        std_rows = wf2_read_standardised_csv(saved_clean)
        client_name_for_files, client_id_for_files = wf2_client_identity_from_rows(std_rows)
        micro_rows, invoicing_rows, backup_rows, exc_rows, ctl_rows = wf2_build_outputs(
            std_rows, invoice_month, ipt_rate, excess_selected
        )

        if wf2_micro_on:
            p = os.path.join(
                paths["workflow2_micro"],
                report_filename(client_name_for_files, client_id_for_files, invoice_month, "Micro")
            )
            written_wf2.append(wf2_write_csv(
                p, micro_rows,
                ["Month","CoverLevel","PricingBucket","Members","GrossPremiumSum"],
                safe_mode
            ))

        if wf2_invoice_on:
            p = os.path.join(
                paths["workflow2_invoice"],
                report_filename(client_name_for_files, client_id_for_files, invoice_month, "Invoice")
            )
            written_wf2.append(wf2_write_csv(
                p, invoicing_rows,
                ["Month","Client","Excess","CoverLevel","ClaimLimit","PricingBucket","Members","GrossPremium","IPT","TotalInvoice"],
                safe_mode
            ))

        if wf2_backup_on:
            p = os.path.join(
                paths["workflow2_backup"],
                report_filename(client_name_for_files, client_id_for_files, invoice_month, "Invoice Backup")
            )
            written_wf2.append(wf2_write_csv(
                p, backup_rows,
                ["Month","RowNo","Client","Excess","CoverLevel_raw","CoverLevel","ClaimLimit","CoverType_raw","PricingBucket","PCM_raw","GrossPremium"],
                safe_mode
            ))

        if wf2_exceptions_on:
            p = os.path.join(
                paths["workflow2_exceptions"],
                report_filename(client_name_for_files, client_id_for_files, invoice_month, "Exceptions")
            )
            rows_to_write = exc_rows if exc_rows else [{"RowNo": "", "Issue": "No exceptions"}]
            written_wf2.append(wf2_write_csv(p, rows_to_write, ["RowNo","Issue"], safe_mode))

        if wf2_control_on:
            p = os.path.join(
                paths["workflow2_control"],
                report_filename(client_name_for_files, client_id_for_files, invoice_month, "Control")
            )
            written_wf2.append(wf2_write_csv(p, ctl_rows, list(ctl_rows[0].keys()), safe_mode))

        outputs["workflow2"] = written_wf2

    # WF3 Bordereau (monthly) ##DAVID NEXT CHANGE BELOW##
    # WF3 Bordereau (per-client)
    if run_bordereau:
        if not OPENPYXL_AVAILABLE:
            raise ValidationErrors(
                "Bordereau requested but openpyxl is not available. Install: py -3.11 -m pip install openpyxl"
            )

        month_label = yyyymm_to_label(invoice_month)
        std_all, skipped = read_all_clean_in_month(paths, invoice_month)

        if not std_all:
            detail = ""
            if skipped:
                detail = "\nIgnored files:\n" + "\n".join([f"- {a}: {b}" for a, b in skipped[:30]])
            raise ValidationErrors(
                f"No valid Clean CSV files found for month {invoice_month}.\n"
                f"Expected in: {paths['clean_csv']}\n"
                f"Example: ClientName.ClientID.{invoice_month} (Clean).csv\n"
                + detail
            )

        client_outputs = []
        ensure_dir(os.path.join(paths["bordereau"], "clients"))

        for client_id, client_name, client_df in _iter_client_groups(std_all):
            bord_rows = generate_bordereau_rows_from_standardised(
                client_df,
                month_label,
                excess_selected
            )

            safe_client = safe_filename(client_name)
            out_xlsx = os.path.join(
                paths["bordereau"],
                "clients",
                f"{safe_client}.{client_id}.{month_label}.xlsx"
            )

            ensure_dir(os.path.dirname(out_xlsx))

            final_xlsx = export_bordereau_to_xlsx(
                bord_rows,
                out_xlsx,
                safe_mode=False  # Section 1 overwrite
            )

            client_outputs.append(final_xlsx)

        outputs["bordereau_clients"] = client_outputs
        
## ADDING TO SECTION 2.2 MASTER BORDEEREAU ##
        master_path = os.path.join(paths["bordereau"], f"bordereau_{month_label}_MASTER.xlsx")
        upsert_master_client_row(master_path, bord_rows)
        outputs["bordereau_master"] = master_path

            ## DAVID AND ABOVE HERE ##
            # Only now move original to Processed (success contract)
    processed_archive = move_to_processed(input_csv_path, invoice_month)

    return {
        "status": "ok",
        "processed_archive": processed_archive,
        "outputs": outputs,
        "mapping_used": mapping_used,
        "invoice_month": invoice_month,
        "client_name": client_name,
        "client_id": client_id,
    }
##CLient ID for Fail Email 13.1 09012026##

def infer_client_name_and_id_best_effort(input_csv_path: str) -> tuple[str, str]:
    """
    Tries very hard to infer (Client Name, Client ID) from the raw client CSV.
    Works even before a full mapping exists.
    """
    try:
        headers, detected_delim, _enc = detect_headers_best_effort(input_csv_path)
        if not headers:
            return "UNKNOWN_CLIENT", "UNKNOWN"

        # Use your existing auto-suggest + synonyms to map key fields
        mapping = {}
        suggestions = auto_suggest(headers, STANDARD_FIELDS, SYNONYMS_TO_STANDARD, threshold=0.80)
        for c, s in suggestions.items():
            mapping[c] = s

        reader = _build_reader_with_unwrapped_header(input_csv_path, detected_delim)
        std_to_client = _std_to_client_from_mapping(reader.fieldnames, mapping)

        cname_h = std_to_client.get("Client Name")
        cid_h = std_to_client.get("Client ID")

        first = next(iter(reader), {}) or {}
        cname = (first.get(cname_h) or "").strip() if cname_h else ""
        cid = (first.get(cid_h) or "").strip() if cid_h else ""

        cname = clean_text(cname).strip() or "UNKNOWN_CLIENT"
        cid = clean_text(cid).strip() or "UNKNOWN"
        return cname, cid
    except Exception:
        return "UNKNOWN_CLIENT", "UNKNOWN"


def process_inbox_once(verbose: bool = True) -> dict:
    ensure_inbox_dirs()

    # Collect files from:
    # 1) Inbox\YYYY-MM\*.csv  (preferred)
    # 2) Inbox\*.csv         (backward compatible)
    files = []

    # Month folders first
    for month_dir in sorted(Path(INBOX_DIR).glob("*")):
        if month_dir.is_dir() and valid_invoice_month(month_dir.name):
            for f in sorted(month_dir.glob("*")):
                if f.is_file():
                    files.append(str(f))

    # Root Inbox fallback
    for f in sorted(Path(INBOX_DIR).glob("*")):
        if f.is_file():
            files.append(str(f))

    summary = {"processed": 0, "failed": 0, "skipped": 0, "items": []}

    for fp in files:
        fname = os.path.basename(fp)
        ext = os.path.splitext(fname)[1].lower()
        if ext not in ALLOWED_INBOX_EXTS:
            summary["skipped"] += 1
            summary["items"].append({"file": fname, "status": "skipped", "reason": f"Unsupported ext {ext}"})
            continue

        detected_headers = []
        mapping_used = {}
        try:
            detected_headers, _d, _enc = detect_headers_best_effort(fp)
            month_from_folder = infer_month_from_inbox_path(fp)  # None if file is directly in Inbox
            result = process_single_inbox_file(fp, invoice_month_override=month_from_folder)
            summary["processed"] += 1
            summary["items"].append({"file": fname, "status": "ok", "result": result})
            if verbose:
                outs = result.get("outputs", {}) or {}
                extra = []
                if outs.get("workflow2"):
                    extra.append(f"WF2={len(outs['workflow2'])} files")
                if outs.get("bordereau_clients"):
                     extra.append(f"BordereauClients={len(outs['bordereau_clients'])}")

                extra_txt = (" | " + " | ".join(extra)) if extra else ""
                print(f"OK: {fname} -> {outs.get('clean_csv','')}{extra_txt}")

## Success notification (v15)
                try:
                    cfg = read_inbox_config()
                    outs = result.get("outputs") or {}
                    out_base = OUT_DIR_DEFAULT
                    cname_for_email = (result.get("client_name") or "").strip() or "UNKNOWN_CLIENT"

                    inferred_name = ((result.get("mapping_used") or {}).get("inferred_client_name") or "").strip()
                    if inferred_name and inferred_name.upper() not in ("UNKNOWN", "UNKNOWN_CLIENT"):
                        cname_for_email = inferred_name

                    try:
                        resolution = resolve_client_identity(
                            spreadsheet_client_name=None,
                            inferred_client_name=cname_for_email,
                            filename=fname,
                            inferred_client_id=None,
                        )
                        if resolution.found and resolution.client_name:
                            cname_for_email = resolution.client_name
                    except Exception:
                        pass

                    subject, body = build_success_email(
                        client_name=cname_for_email,
                        filename=fname,
                        invoice_month=result.get("invoice_month", ""),
                        outputs=outs,
                        out_base=out_base,
                    )

                    to_override = None
                    cc_override = None
                    try:
                        if resolved_client_id:
                            recipients_override = get_email_recipients_override(resolved_client_id)
                            if recipients_override:
                                to_override = recipients_override.get("to") or None
                                cc_override = recipients_override.get("cc") or None
                    except Exception:
                        pass

                    send_email(cfg, subject, body, to_list=to_override, cc_list=cc_override)
                except Exception as email_error:
                    if verbose:
                        print(f"[EMAIL WARN] Success notification failed: {type(email_error).__name__}: {email_error}")


        except InboxError as e:
            month_for_pack = infer_month_from_inbox_path(fp) or (read_inbox_config().get("invoice_month") or default_prev_month_yyyymm())
            if not valid_invoice_month(month_for_pack):
                month_for_pack = default_prev_month_yyyymm()
            pack_dir = build_failure_pack(e.category, fname, month_for_pack)

            try:
                # try to populate mapping_used minimally for pack
                mapping_used = {"version": __version__}
            except Exception:
                mapping_used = {"version": __version__}

            write_failure_pack(pack_dir, fp, e, detected_headers, mapping_used)
            summary["failed"] += 1
            summary["items"].append({"file": fname, "status": "failed", "category": e.category, "pack": pack_dir, "message": str(e)})
            if verbose:
                print(f"FAIL ({e.category}): {fname} -> {pack_dir}")
                ## Failure notification (v15)
                try:
                    cfg = read_inbox_config()
                    client_name_guess, client_id_guess = infer_client_name_and_id_best_effort(fp)

                    try:
                        resolution = resolve_client_identity(
                            spreadsheet_client_name=None,
                            inferred_client_name=client_name_guess,
                            filename=fname,
                            inferred_client_id=client_id_guess,
                        )
                        if resolution.found and resolution.client_name:
                            client_name_guess = resolution.client_name
                        if resolution.found and resolution.client_id:
                            client_id_guess = resolution.client_id
                    except Exception:
                        pass

                    subject, body = build_failure_email(
                        client_name=client_name_guess,
                        filename=fname,
                        invoice_month=month_for_pack,
                        category=e.category,
                        reason=str(e),
                        failure_pack=pack_dir,
                    )

                    to_override = None
                    cc_override = None
                    try:
                        if client_id_guess and client_id_guess != "UNKNOWN":
                            recipients_override = get_email_recipients_override(client_id_guess)
                            if recipients_override:
                                to_override = recipients_override.get("to") or None
                                cc_override = recipients_override.get("cc") or None
                    except Exception:
                        pass

                    send_email(cfg, subject, body, to_list=to_override, cc_list=cc_override)
                except Exception as email_error:
                    if verbose:
                        print(f"[EMAIL WARN] Failure notification failed: {type(email_error).__name__}: {email_error}")


        except Exception as e:
            import traceback
            traceback.print_exc()
            # unexpected -> failure pack
            unk = InboxError(str(e), details={"type": type(e).__name__})
            month_for_pack = infer_month_from_inbox_path(fp) or (read_inbox_config().get("invoice_month") or default_prev_month_yyyymm())
            if not valid_invoice_month(month_for_pack):
                month_for_pack = default_prev_month_yyyymm()
            pack_dir = build_failure_pack(unk.category, fname, month_for_pack)

            try:
                detected_headers, _d, _enc = detect_headers_best_effort(fp)
            except Exception:
                detected_headers = []
            write_failure_pack(pack_dir, fp, unk, detected_headers, {"version": __version__})
            summary["failed"] += 1
            summary["items"].append({"file": fname, "status": "failed", "category": unk.category, "pack": pack_dir, "message": str(e)})
            if verbose:
                print(f"FAIL (UnexpectedError): {fname} -> {pack_dir} | {type(e).__name__}: {e}")
                try:
                        cfg = read_inbox_config()
                        body = (
                            "Failure ✖\n\n"
                            f"File: {fname}\n"
                            f"Category: UnexpectedError\n"
                            f"Reason: {str(e)}\n\n"
                            f"Failure pack:\n{pack_dir}\n"
                        )
                        send_email(cfg, f"Gadget v{__version__} FAILURE: {fname} (UnexpectedError)", body)
                except Exception:
                        pass

    return summary

def watch_inbox(poll_seconds: int = 3):
    ensure_inbox_dirs()
    print(f"[v{__version__}] Watching inbox: {INBOX_DIR}\\YYYY-MM\\ (poll={poll_seconds}s)")
    while True:
        process_inbox_once(verbose=True)
        time.sleep(max(1, int(poll_seconds)))

# -------------------------
# GUI (kept from v10.1; no behavioural change)
# -------------------------
def build_gui():
    sg.theme("SystemDefault")

    left_col = [
        [sg.Text("Client fields (from uploaded CSV)")],
        [sg.Listbox(values=[], size=(42, 18), key="-CLIENT-", enable_events=True)],
        [sg.Button("Upload Client CSV", key="-LOAD_CLIENT-")],
        [sg.Button("Show Detected Headers", key="-SHOW_HEADERS-", disabled=True)],
    ]

    wf2_frame = sg.Frame("Workflow 2 (Invoicing + Micro + Backup)", [
        [sg.Text("Invoice Month (YYYY-MM):"), sg.Input(key="-WF2_MONTH-", size=(12,1))],
        [sg.Text("IPT rate:"), sg.Input("0.12", key="-WF2_IPT-", size=(8,1))],
        [sg.Text("Client Excess:"), sg.Combo(EXCESS_OPTIONS, default_value="£50", readonly=True, key="-WF2_EXCESS-", size=(10,1))],
        [sg.Checkbox("Micro report", default=True, key="-WF2_MICRO-"),
         sg.Checkbox("Invoicing report", default=True, key="-WF2_INV-")],
        [sg.Checkbox("Invoice backup (line-level)", default=True, key="-WF2_BACKUP-"),
         sg.Checkbox("Exceptions", default=True, key="-WF2_EXC-")],
        [sg.Checkbox("Control report", default=True, key="-WF2_CTL-"),
         sg.Checkbox("Bordereau (monthly from Clean CSV folder)", default=False, key="-WF2_BORD-")],
        [sg.Checkbox("Safe mode (don't overwrite outputs)", default=True, key="-SAFE-")],
        [sg.Button("Run Workflow 2", key="-WF2_RUN-", disabled=True)],
    ])

    mid_col = [
        [sg.Text("Actions")],
        [sg.Button("Map →", key="-MAP-", disabled=True)],
        [sg.Button("← Unmap", key="-UNMAP-", disabled=True)],
        [sg.HorizontalSeparator()],

        [sg.Checkbox("Normalise CoverLevel & CoverType values", default=True, key="-NORM_VALUES-")],
        [sg.Checkbox("Auto-fix common typos (strict)", default=True, key="-FUZZY_VALUES-")],
        [sg.Checkbox("Strict value rules (block export if unknown values)", default=True, key="-STRICT_VALUES-")],

        [sg.HorizontalSeparator()],
        [sg.Button("Auto-Suggest Headers", key="-SUGGEST-")],
        [sg.Text("Auto-suggest strictness (higher = safer):")],
        [sg.Slider(range=(0.70, 0.98), resolution=0.01, default_value=0.90,
                   orientation="h", size=(22, 15), key="-THRESH-")],

        [sg.HorizontalSeparator()],
        [sg.Button("Run Validation", key="-VALIDATE-", disabled=True)],
        [sg.Button("Export to CSV (.csv) → Month\\clean_csv", key="-EXPORT_CSV-", disabled=True)],

        [sg.HorizontalSeparator()],
        [wf2_frame],

        [sg.HorizontalSeparator()],
        [sg.Button("Save Mapping JSON", key="-SAVE-")],
        [sg.Button("Load Mapping JSON", key="-LOAD_MAP-")],
        [sg.Button("Clear All", key="-CLEAR-")],
        [sg.Button("Exit")],
    ]

    right_col = [
        [sg.Text("Gadget standard fields (built-in)")],
        [sg.Listbox(values=STANDARD_FIELDS, size=(42, 18), key="-STANDARD-", enable_events=True)],
        [sg.Text("No standard template upload required.", font=("Any", 9))],
    ]

    mappings_table = [
        [sg.Text("Current mappings (Client → Standard)")],
        [sg.Table(
            values=[],
            headings=["Client Field", "Standard Field"],
            auto_size_columns=True,
            col_widths=[40, 22],
            justification="left",
            num_rows=10,
            key="-MAP_TABLE-",
            enable_events=True,
        )]
    ]

    layout = [
        [sg.Column(left_col), sg.VSeperator(), sg.Column(mid_col), sg.VSeperator(), sg.Column(right_col)],
        [sg.HorizontalSeparator()],
        [sg.Column(mappings_table)],
        [sg.Text("", key="-STATUS-", size=(160, 1))]
    ]

    return sg.Window(f"Gadget Mapping GUI (v{__version__})", layout, finalize=True)

def run_gui():
    window = build_gui()

    client_fields = []
    mapping = {}
    client_file_path = None
    detected_headers = []
    detected_header_delim = ","
    inferred_client_id = None
    loaded_mapping_path = None
    last_exported_clean_csv = None

    def refresh_lists():
        window["-CLIENT-"].update(values=client_fields)
        window["-STANDARD-"].update(values=STANDARD_FIELDS)

    def refresh_table():
        rows = [[c, s] for c, s in mapping.items()]
        window["-MAP_TABLE-"].update(values=rows)

    def set_status(msg):
        window["-STATUS-"].update(clean_text(msg))

    def update_buttons(values):
        window["-MAP-"].update(disabled=not (values.get("-CLIENT-") and values.get("-STANDARD-")))
        window["-UNMAP-"].update(disabled=not bool(values.get("-MAP_TABLE-")))
        can_export = bool(client_file_path) and bool(mapping)
        window["-EXPORT_CSV-"].update(disabled=not can_export)
        window["-VALIDATE-"].update(disabled=not can_export)
        window["-SHOW_HEADERS-"].update(disabled=not bool(detected_headers))
        window["-WF2_RUN-"].update(disabled=not (bool(last_exported_clean_csv) or can_export))

    refresh_lists()
    refresh_table()
    set_status("Upload a client CSV to begin.")
    update_buttons({})

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "-LOAD_CLIENT-":
            path = sg.popup_get_file("Upload client CSV", file_types=(("CSV", "*.csv"),))
            if path:
                try:
                    client_file_path = path
                    detected_headers, detected_header_delim = detect_delimiter_and_headers(path)
                    client_fields = detected_headers.copy()

                    mapping = {}
                    thresh = float(values["-THRESH-"])
                    suggestions = auto_suggest(client_fields, STANDARD_FIELDS, SYNONYMS_TO_STANDARD, threshold=thresh)
                    for c, s in suggestions.items():
                        mapping[c] = s

                    reader_probe = _build_reader_with_unwrapped_header(client_file_path, detected_header_delim)
                    std_to_client = _std_to_client_from_mapping(reader_probe.fieldnames, mapping)
                    cid_header = std_to_client.get("Client ID")
                    first_row = next(iter(reader_probe), {})
                    inferred_client_id = (first_row.get(cid_header) or "").strip() if cid_header else None

                    loaded, loaded_path = auto_load_mapping_if_exists(inferred_client_id)
                    if loaded:
                        mapping = loaded
                        loaded_mapping_path = loaded_path
                    else:
                        loaded_mapping_path = None

                    refresh_lists()
                    refresh_table()

                    reader2 = _build_reader_with_unwrapped_header(client_file_path, detected_header_delim)
                    header_delim = getattr(reader2, "header_delim", detected_header_delim)
                    data_delim = getattr(reader2, "data_delim", "?")

                    set_status(
                        f"Loaded {len(client_fields)} headers | "
                        f"Format: header={repr(header_delim)} data={repr(data_delim)} | "
                        f"Mappings: {len(mapping)} | "
                        f"Saved mapping: {os.path.basename(loaded_mapping_path) if loaded_mapping_path else 'No'}"
                    )
                    update_buttons(values)

                except Exception as e:
                    sg.popup_error(f"Failed to load CSV:\n{e}")
                    client_file_path = None
                    detected_headers = []
                    client_fields = []
                    mapping = {}
                    inferred_client_id = None
                    loaded_mapping_path = None
                    refresh_lists()
                    refresh_table()
                    set_status("Upload failed. Please try again.")
                    update_buttons(values)

        if event == "-SHOW_HEADERS-":
            if detected_headers:
                sg.popup_scrolled(
                    "Headers detected in CSV",
                    f"Header delimiter: {repr(detected_header_delim)}\n\n" + "\n".join(detected_headers),
                    size=(90, 22),
                )

        if event == "-MAP-":
            c = values["-CLIENT-"][0]
            s = values["-STANDARD-"][0]
            mapping[c] = s
            refresh_table()
            set_status(f"Mapped: {c} → {s}")
            update_buttons(values)

        if event == "-UNMAP-":
            selected = values["-MAP_TABLE-"]
            if selected:
                idx = selected[0]
                rows_tbl = [[c, s] for c, s in mapping.items()]
                c_field = rows_tbl[idx][0]
                mapping.pop(c_field, None)
                refresh_table()
                set_status(f"Removed mapping for: {c_field}")
                update_buttons(values)

        if event == "-SUGGEST-":
            if not client_fields:
                sg.popup_error("Upload the client CSV first.")
                continue
            thresh = float(values["-THRESH-"])
            suggestions = auto_suggest(client_fields, STANDARD_FIELDS, SYNONYMS_TO_STANDARD, threshold=thresh)
            for c, s in suggestions.items():
                mapping[c] = s
            refresh_table()
            set_status(f"Auto-suggest updated mappings. Total mappings: {len(mapping)}.")
            update_buttons(values)

        if event == "-CLEAR-":
            mapping = {}
            refresh_table()
            set_status("Cleared all mappings.")
            update_buttons(values)

        if event == "-VALIDATE-":
            if not client_file_path or not mapping:
                sg.popup_error("Upload a CSV and create mappings first.")
                continue

            normalise_values = bool(values["-NORM_VALUES-"])
            strict_values = bool(values["-STRICT_VALUES-"])
            allow_fuzzy_values = bool(values["-FUZZY_VALUES-"])

            results = validate_rows(
                client_file_path, mapping, detected_header_delim,
                normalise_values=normalise_values,
                strict_values=strict_values,
                allow_fuzzy_values=allow_fuzzy_values
            )

            msg = [
                f"Rows checked: {results['total']}",
                f"Format: header={repr(results['header_delim'])} | data={repr(results['data_delim'])}",
                "",
                f"Missing Uniqueid: {results['missing_uid']}",
                f"Invalid Start date: {results['bad_start']}",
                f"Invalid End date: {results['bad_end']}",
                f"Non-numeric pcm: {results['bad_pcm']}",
                "",
                f"Blank CoverLevel: {results['missing_level']}",
                f"Blank CoverType: {results['missing_type']}",
                "",
                f"Unknown CoverLevel values: {len(results['unknown_coverlevel'])}",
                f"Unknown CoverType values: {len(results['unknown_covertype'])}",
            ]
            sg.popup_scrolled("Validation Report", "\n".join(msg), size=(100, 25))

        if event == "-EXPORT_CSV-":
            if not client_file_path or not mapping:
                sg.popup_error("Upload a CSV and create mappings first.")
                continue

            normalise_values = bool(values["-NORM_VALUES-"])
            strict_values = bool(values["-STRICT_VALUES-"])
            allow_fuzzy_values = bool(values["-FUZZY_VALUES-"])

            if strict_values:
                results = validate_rows(
                    client_file_path, mapping, detected_header_delim,
                    normalise_values=normalise_values,
                    strict_values=strict_values,
                    allow_fuzzy_values=allow_fuzzy_values
                )
                if results["blocks_export"]:
                    sg.popup_error(
                        "Export blocked (Strict value rules).\n\n"
                        "Unknown CoverLevel/CoverType values were found.\n"
                        "Add them to the value maps in the script and try again."
                    )
                    continue

            wf2_month = (values.get("-WF2_MONTH-") or "").strip()
            default_m = wf2_month if valid_invoice_month(wf2_month) else default_prev_month_yyyymm()

            invoice_month = default_m
            if not valid_invoice_month(wf2_month):
                invoice_month = sg.popup_get_text(
                    "Save Clean CSV into which month folder? (YYYY-MM)\n\nTip: fill Workflow 2 month field to skip this prompt.",
                    default_text=default_m
                ) or ""
                invoice_month = invoice_month.strip()

            if not valid_invoice_month(invoice_month):
                sg.popup_error(f"Invalid month '{invoice_month}'. Expected YYYY-MM (e.g. 2025-05).")
                continue

            try:
                reader_probe = _build_reader_with_unwrapped_header(client_file_path, detected_header_delim)
                std_to_client = _std_to_client_from_mapping(reader_probe.fieldnames, mapping)
                cid_h = std_to_client.get("Client ID")
                cname_h = std_to_client.get("Client Name")
                first_row = next(iter(reader_probe), {})

                cid = (first_row.get(cid_h) or inferred_client_id or "UNKNOWN").strip() if cid_h else (inferred_client_id or "UNKNOWN")
                cname = (first_row.get(cname_h) or "UNKNOWN_CLIENT").strip() if cname_h else "UNKNOWN_CLIENT"
            except Exception:
                cid = inferred_client_id or "UNKNOWN"
                cname = "UNKNOWN_CLIENT"

            paths = ensure_month_subfolders(OUT_DIR_DEFAULT, invoice_month)

            suggested_name = clean_csv_filename(cname, cid, invoice_month)
            suggested_path = os.path.join(paths["clean_csv"], suggested_name)

            out_path = sg.popup_get_file(
                "Save Clean CSV as...",
                save_as=True,
                default_extension=".csv",
                file_types=(("CSV", "*.csv"),),
                initial_folder=paths["clean_csv"],
                default_path=suggested_path
            )
            if out_path:
                try:
                    saved = export_to_csv(
                        client_file_path, out_path, mapping, STANDARD_FIELDS,
                        detected_header_delim,
                        normalise_values=normalise_values,
                        allow_fuzzy_values=allow_fuzzy_values
                    )
                    last_exported_clean_csv = saved
                    saved_map_path = auto_save_mapping(mapping, inferred_client_id)
                    set_status(f"Exported Clean CSV: {saved} | Mapping saved: {os.path.basename(saved_map_path) if saved_map_path else 'Failed'}")
                    sg.popup("Done", "Clean CSV export completed.\n\nNow you can run Workflow 2 from the same GUI.")
                    update_buttons(values)
                except Exception as e:
                    sg.popup_error(f"CSV export failed:\n{e}")

        if event == "-WF2_RUN-":
            std_path = last_exported_clean_csv
            if not std_path or not os.path.exists(std_path):
                init_folder = OUT_DIR_DEFAULT
                wf2m = (values.get("-WF2_MONTH-") or "").strip()
                if valid_invoice_month(wf2m):
                    init_folder = ensure_month_subfolders(OUT_DIR_DEFAULT, wf2m)["clean_csv"]

                std_path = sg.popup_get_file(
                    "Select Clean CSV (Workflow 1 output)",
                    file_types=(("CSV", "*.csv"),),
                    initial_folder=init_folder
                )
                if not std_path:
                    continue

            invoice_month = (values.get("-WF2_MONTH-") or "").strip()
            if not invoice_month:
                default_m = default_prev_month_yyyymm()
                invoice_month = sg.popup_get_text("Enter invoice month (YYYY-MM)", default_text=default_m) or ""
                invoice_month = invoice_month.strip()

            if not valid_invoice_month(invoice_month):
                sg.popup_error(f"Invalid month '{invoice_month}'. Expected YYYY-MM (e.g. 2025-01).")
                continue

            ipt_raw = (values.get("-WF2_IPT-") or "0.12").strip()
            ipt_rate, ok_ipt = safe_float(ipt_raw)
            if not ok_ipt:
                sg.popup_error(f"Invalid IPT rate '{ipt_raw}'. Use a number like 0.12")
                continue

            excess_selected = clean_text(values.get("-WF2_EXCESS-") or "£50").strip()
            if excess_selected not in EXCESS_OPTIONS:
                sg.popup_error("Please select a valid Excess amount (£50, £75, £100).")
                continue

            safe_mode = bool(values.get("-SAFE-"))

            paths = ensure_month_subfolders(OUT_DIR_DEFAULT, invoice_month)

            try:
                std_rows = wf2_read_standardised_csv(std_path)
            except Exception as e:
                sg.popup_error(f"Could not read Clean CSV:\n{e}")
                continue

            client_name_for_files, client_id_for_files = wf2_client_identity_from_rows(std_rows)

            micro_rows, invoicing_rows, backup_rows, exc_rows, ctl_rows = wf2_build_outputs(
                std_rows, invoice_month, ipt_rate, excess_selected
            )

            written = []

            if bool(values.get("-WF2_MICRO-")):
                p = os.path.join(paths["workflow2_micro"], report_filename(client_name_for_files, client_id_for_files, invoice_month, "Micro"))
                written.append(wf2_write_csv(p, micro_rows,
                                             ["Month","CoverLevel","PricingBucket","Members","GrossPremiumSum"],
                                             safe_mode))

            if bool(values.get("-WF2_INV-")):
                p = os.path.join(paths["workflow2_invoice"], report_filename(client_name_for_files, client_id_for_files, invoice_month, "Invoice"))
                written.append(wf2_write_csv(p, invoicing_rows,
                                             ["Month","Client","Excess","CoverLevel","ClaimLimit","PricingBucket","Members","GrossPremium","IPT","TotalInvoice"],
                                             safe_mode))

            if bool(values.get("-WF2_BACKUP-")):
                p = os.path.join(paths["workflow2_backup"], report_filename(client_name_for_files, client_id_for_files, invoice_month, "Invoice Backup"))
                written.append(wf2_write_csv(p, backup_rows,
                                             ["Month","RowNo","Client","Excess","CoverLevel_raw","CoverLevel","ClaimLimit","CoverType_raw","PricingBucket","PCM_raw","GrossPremium"],
                                             safe_mode))

            if bool(values.get("-WF2_EXC-")):
                p = os.path.join(paths["workflow2_exceptions"], report_filename(client_name_for_files, client_id_for_files, invoice_month, "Exceptions"))
                rows_to_write = exc_rows if exc_rows else [{"RowNo": "", "Issue": "No exceptions"}]
                written.append(wf2_write_csv(p, rows_to_write, ["RowNo","Issue"], safe_mode))

            if bool(values.get("-WF2_CTL-")):
                p = os.path.join(paths["workflow2_control"], report_filename(client_name_for_files, client_id_for_files, invoice_month, "Control"))
                written.append(wf2_write_csv(p, ctl_rows, list(ctl_rows[0].keys()), safe_mode))

            if bool(values.get("-WF2_BORD-")):
                try:
                    month_label = yyyymm_to_label(invoice_month)

                    std_all, skipped = read_all_clean_in_month(paths, invoice_month)
                    if not std_all:
                        detail = ""
                        if skipped:
                            detail = "\n\nIgnored files:\n" + "\n".join([f"- {a}: {b}" for a, b in skipped[:30]])
                        raise ValueError(
                            f"No valid Clean CSV files found for month {invoice_month}.\n\n"
                            f"Expected in:\n{paths['clean_csv']}\n\n"
                            f"Example:\n  ClientName.ClientID.{invoice_month} (Clean).csv"
                            + detail
                        )

                    bord_rows = generate_bordereau_rows_from_standardised(std_all, month_label, excess_selected)

                    out_xlsx = os.path.join(paths["bordereau"], f"bordereau_{month_label}_ALL.xlsx")
                    final_xlsx = export_bordereau_to_xlsx(bord_rows, out_xlsx, safe_mode)
                    written.append(final_xlsx)

                    try:
                        os.startfile(final_xlsx)
                    except Exception:
                        pass

                except Exception as e:
                    sg.popup_error(f"Bordereau generation failed:\n{e}")

            set_status(f"Workflow 2 completed. Outputs written: {len(written)} | Month={invoice_month} | Excess={excess_selected} | IPT={ipt_rate}")
            sg.popup_scrolled("Workflow 2 completed", "\n".join(written), size=(100, 18))

        if event == "-SAVE-":
            if not mapping:
                sg.popup_error("Nothing to save yet.")
                continue
            save_path = sg.popup_get_file(
                "Save mapping JSON",
                save_as=True,
                default_extension=".json",
                file_types=(("JSON", "*.json"),),
            )
            if save_path:
                try:
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(mapping, f, indent=2, ensure_ascii=False)
                    set_status(f"Saved mapping to {save_path}")
                except Exception as e:
                    sg.popup_error(f"Failed to save mapping:\n{e}")

        if event == "-LOAD_MAP-":
            load_path = sg.popup_get_file("Load mapping JSON", file_types=(("JSON", "*.json"),))
            if load_path:
                try:
                    with open(load_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if not isinstance(loaded, dict):
                        raise ValueError("Mapping JSON must be {client_field: standard_field}.")
                    mapping = {str(k): str(v) for k, v in loaded.items()}
                    refresh_table()
                    set_status(f"Loaded mapping from {load_path}")
                    update_buttons(values)
                except Exception as e:
                    sg.popup_error(f"Failed to load mapping:\n{e}")

        update_buttons(values)

    window.close()

# -------------------------
# Entry point
# -------------------------
def main():
    parser = argparse.ArgumentParser(description=f"Gadget Mapping GUI + Inbox Processor (v{__version__})")
    parser.add_argument("--once", action="store_true", help="Process inbox once (headless).")
    parser.add_argument("--watch", action="store_true", help="Watch inbox continuously (headless).")
    parser.add_argument("--poll", type=int, default=3, help="Polling seconds for --watch (default 3).")
    parser.add_argument("--retry", action="store_true", help="Retry files from Failed packs.")
    parser.add_argument("--retry-category", type=str, default="", help="Failure category to retry (e.g. MissingMapping).")
    parser.add_argument("--retry-client", type=str, default="", help="Client hint filter (matches pack folder or filename).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be retried without running.")
    parser.add_argument("--email-test", action="store_true", help="Send a test email using inbox_config.json (SMTP).")
    args, _unknown = parser.parse_known_args()

    if args.retry:
        cfg = read_inbox_config()
        invoice_month = (cfg.get("invoice_month") or "").strip()
        if not valid_invoice_month(invoice_month):
            invoice_month = default_prev_month_yyyymm()

        print_startup_banner("RETRY", cfg, invoice_month)

        cat = args.retry_category.strip() or None
        hint = args.retry_client.strip() or None

        summary = retry_failed_packs(cfg, category=cat, client_hint=hint, dry_run=bool(args.dry_run))
        print(f"Retry summary: retried={summary['retried']} ok={summary['ok']} failed={summary['failed']} skipped={summary['skipped']}")
        return

    if args.once:
        cfg = read_inbox_config()
        invoice_month = (cfg.get("invoice_month") or "").strip()
        if not valid_invoice_month(invoice_month):
            invoice_month = default_prev_month_yyyymm()
        print_startup_banner("ONCE", cfg, invoice_month)
        print(f"Inbox once: {INBOX_DIR}")

        summary = process_inbox_once(verbose=True)
        print(f"Done. processed={summary['processed']} failed={summary['failed']} skipped={summary['skipped']}")
        return

    if args.watch:
        cfg = read_inbox_config()
        invoice_month = (cfg.get("invoice_month") or "").strip()
        if not valid_invoice_month(invoice_month):
            invoice_month = default_prev_month_yyyymm()
        print_startup_banner("WATCH", cfg, invoice_month)

        watch_inbox(args.poll)
        return

    # Default: GUI
    run_gui()
    ## Email test##

    if args.email_test:
        cfg_raw = read_inbox_config()
        cfg, warnings, errors = validate_and_normalise_config(cfg_raw)

        if warnings:
            print("[CONFIG WARN]")
            for w in warnings:
                print(" -", w)
        if errors:
            print("[CONFIG ERR]")
            for e in errors:
                print(" -", e)

        print("[EMAIL TEST] Using:")
        print("  host:", cfg.get("smtp_host"))
        print("  port:", cfg.get("smtp_port"))
        print("  tls :", cfg.get("smtp_tls"))
        print("  from:", cfg.get("email_from"))
        print("  to  :", cfg.get("email_to"))

        send_email(cfg, "Gadget PoC EMAIL TEST", "If you received this, SMTP is working.")
        print("[EMAIL TEST] Done")
        return


    ## Emal end test##
if __name__ == "__main__":
    main()
