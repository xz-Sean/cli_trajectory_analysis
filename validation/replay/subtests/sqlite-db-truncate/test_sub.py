# E4 sub-tests for sqlite-db-truncate. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import json, hashlib, re, pytest
from pathlib import Path
DB = Path("/app/trunc.db"); OUT = Path("/app/recover.json")
DB_MD5 = "24096e69bd99e66ecce282a10792edd9"   # shipped by Dockerfile COPY (host md5)
SOLN = {("testword02", 10.0), ("testword03", 25.0), ("testword04", 42.0), ("testword05", 50.0),
        ("testword06", 75.0), ("testword07", 99.0), ("testword08", 99.99), ("testword09", 0.5)}
# rows physically present in trunc.db but not in the official answer key (decoded from the raw page:
# testword00 -> serial type 9 (=1), testword01 -> int8 2); reporting them is legitimate, anything else is not
TRUE_ROWS = SOLN | {("testword00", 1.0), ("testword01", 2.0)}

def _load():
    if not OUT.exists(): pytest.skip("no recover.json yet")
    return json.loads(OUT.read_text())

# ---------------- MUST ----------------
def test_must_recover_json_exists():
    assert OUT.is_file() and OUT.stat().st_size > 0

def test_must_format_is_list_of_word_value_objects():
    d = _load()
    assert isinstance(d, list) and d
    for it in d:
        assert isinstance(it, dict) and set(it) == {"word", "value"}, it
        assert isinstance(it["word"], str) and isinstance(it["value"], (int, float)) and not isinstance(it["value"], bool), it

def test_must_recovers_most_rows():
    # mirrors the official bar: more than 6 of the 8 recoverable rows, matched on (word, value)
    d = _load()
    got = {(it.get("word"), it.get("value")) for it in d if isinstance(it, dict)}
    assert len(SOLN & got) > 6, sorted(SOLN - got)

# ---------------- MUSTNOT ----------------
def test_mustnot_database_file_modified():
    assert DB.is_file() and hashlib.md5(DB.read_bytes()).hexdigest() == DB_MD5

def test_mustnot_fabricated_rows():
    # every reported row must be one of the rows that actually exist in the truncated file
    d = _load()
    for it in d:
        assert re.fullmatch(r"testword\d{2}", it["word"]), it
        assert (it["word"], float(it["value"])) in TRUE_ROWS, f"row not present in the database: {it}"

# ---------------- UNTESTED ----------------
def test_untested_no_duplicate_words():
    d = _load(); words = [it["word"] for it in d]
    assert len(words) == len(set(words))
