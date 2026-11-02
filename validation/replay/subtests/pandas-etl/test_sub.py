# E4 sub-tests for pandas-etl. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import csv, hashlib, re, pytest
from pathlib import Path
OUT = Path("/app/result.csv"); INP = Path("/app/data.csv")
INP_MD5 = "1469cb45796ec71a622553b5ea96fd6a"   # task-deps/data.csv as COPY'd
COLS = ["participant_id", "first_name", "last_name", "birth_date", "address", "phone_number", "country", "institute",
        "occupation", "register_time", "postal_code", "city", "team_name"]
EXP = {  # participant_id -> (postal_code, city, birth_date, team_name)
    "bd9b6f88-b84f-4c4d-90f8-b67fe2f1a29a": ("80734", "Medan", "1991-02-05", "CN-Georgia-UPM"),
    "7dfe3391-6f40-47b6-b4db-0c76ebaf5fc3": ("09434", "Prabumulih", "1993-01-11", "AS-Korea Utara-UD"),
    "19582d7f-b824-4fe5-a517-d5bf573fc768": ("57739", "Ambon", "1993-07-31", "CH-Komoro-UHP"),
    "aeb6d817-25f3-4867-8a74-8d92e0a0f633": ("76156", "Lubuklinggau", "1991-11-04", "SR-Eritrea-PTY"),
    "1fdabdd9-5444-4c97-87b2-fe8833ad0d27": ("70074", "Kediri", "2003-01-22", "VA-Aljazair-PHR")}

def _rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f); return r.fieldnames, {row["participant_id"]: row for row in r}

def test_must_result_exists():
    assert OUT.exists() and OUT.stat().st_size > 0

def test_must_columns_exactly_as_listed():
    cols, _ = _rows(OUT); assert set(cols) == set(COLS), cols

def test_must_postal_code_extracted():
    _, rows = _rows(OUT)
    for pid, (pc, *_r) in EXP.items(): assert rows[pid]["postal_code"] == pc, (pid, rows[pid]["postal_code"])

def test_must_city_extracted():
    _, rows = _rows(OUT)
    for pid, (_pc, city, *_r) in EXP.items(): assert rows[pid]["city"] == city, (pid, rows[pid]["city"])

def test_must_birth_date_iso_format():
    _, rows = _rows(OUT)
    for pid, (_pc, _c, bd, _t) in EXP.items():
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", rows[pid]["birth_date"]) and rows[pid]["birth_date"] == bd, rows[pid]["birth_date"]

def test_must_team_name_format():
    _, rows = _rows(OUT)
    for pid, (*_r, tn) in EXP.items(): assert rows[pid]["team_name"] == tn, (pid, rows[pid]["team_name"])

def test_mustnot_input_data_modified():
    assert INP.exists() and hashlib.md5(INP.read_bytes()).hexdigest() == INP_MD5

def test_mustnot_rows_dropped_or_added():
    if not OUT.exists(): pytest.skip("no output yet")
    _, rows = _rows(OUT); assert set(rows) == set(EXP), set(rows) ^ set(EXP)

def test_mustnot_additional_columns():
    if not OUT.exists(): pytest.skip("no output yet")
    cols, _ = _rows(OUT); assert not (set(cols) - set(COLS)), set(cols) - set(COLS)

def test_untested_column_order_as_listed():
    cols, _ = _rows(OUT); assert cols == COLS, cols

def test_untested_passthrough_columns_unchanged():
    # columns not named by the four transformations must carry the original values
    _, src = _rows(INP); _, out = _rows(OUT)
    keep = ["first_name", "last_name", "address", "phone_number", "country", "institute", "occupation"]
    for pid in EXP:
        for c in keep: assert out[pid][c] == src[pid][c], (pid, c, out[pid][c], src[pid][c])
        assert float(out[pid]["register_time"]) == float(src[pid]["register_time"])
