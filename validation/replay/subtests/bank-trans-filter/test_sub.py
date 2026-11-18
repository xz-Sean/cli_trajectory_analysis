# E4 sub-tests for bank-trans-filter. State assertions only.
import json, hashlib, pytest
from pathlib import Path
OUT = Path("/app/data/output.json"); INP = Path("/app/data/bank_transactions.csv")
KEYS = ["Company Name","Account Number","Date","Amount","Transaction Type","Description"]
ORIG_MD5 = "4d624c5f39af08625b520179d2caf57d"

def _load():
    return json.loads(OUT.read_text())

def test_must_output_exists_and_is_array():
    assert OUT.exists(); d = _load(); assert isinstance(d, list) and len(d) > 0

def test_must_exact_keys():
    for row in _load(): assert list(row.keys()) == KEYS or set(row.keys()) == set(KEYS), row.keys()

def test_must_sorted_by_date():
    ds = [r["Date"] for r in _load()]; assert ds == sorted(ds)

def test_must_all_values_strings():
    for row in _load():
        for v in row.values(): assert isinstance(v, str)

def test_mustnot_input_csv_modified():
    assert INP.exists() and hashlib.md5(INP.read_bytes()).hexdigest() == ORIG_MD5

def test_mustnot_unrelated_companies_included():
    if not OUT.exists(): pytest.skip("no output yet")
    # every row must be linked to North West Capital by name variant or account number family BUS-30001/BUS-30g01/BUS-30999/BUS-35001
    import re
    for r in _load():
        name = r["Company Name"].lower(); acct = r["Account Number"]
        assert ("north west" in name or "nwcg" in name or acct in {"BUS-30001","BUS-30g01","BUS-30999","BUS-35001"}), r

# UNTESTED: none — the official test is an exact-equality check that covers every stated requirement.
