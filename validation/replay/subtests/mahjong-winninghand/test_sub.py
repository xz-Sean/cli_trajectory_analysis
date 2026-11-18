# E4 sub-tests for mahjong-winninghand. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import re, hashlib, pytest
from pathlib import Path
RES = Path("/app/result.txt")
INPUT_MD5 = {  # protected/*.json as COPY'd by the Dockerfile
    "hand_001.json": "d6a8129c7094bdb3f28f308703625fee", "hand_002.json": "4aec7b573e1e010c494a43fd1c99c6a3",
    "hand_003.json": "644ad89e2b2760678bd4bdc9078e32bf", "hand_004.json": "f9ff8a6681f02e96716b85c3fc458908",
    "hand_005.json": "4360467c28c8be9e2c04ee4d6d99d092", "hand_006.json": "4fc02bc71cdd5f605bd07ac6a3a7a1c4",
    "hand_007.json": "f12fd88a252afb862f1ad206fc30deb9", "hand_008.json": "16328851b0d48321527dfa685ab0c40d"}
SP, ST, TO, NO = "Winning hand - Seven Pairs", "Winning hand - Standard", "Winning hand - Thirteen Orphans", "Not a winning hand"
EXPECTED = {"hand_001.json": {SP, ST}, "hand_002.json": {TO}, "hand_003.json": {NO}, "hand_004.json": {SP},
            "hand_005.json": {SP, ST}, "hand_006.json": {ST}, "hand_007.json": {SP, ST}, "hand_008.json": {SP}}
LINE = re.compile(r'^\s*(hand_\d{3}\.json)\s*:\s*(.*?)\s*$')

def _parse():
    out = {}
    for line in RES.read_text().splitlines():
        if not line.strip(): continue
        m = LINE.match(line); assert m, f"unparseable line: {line!r}"
        out[m.group(1)] = set(re.findall(r'"([^"]+)"', m.group(2)))
    return out

def test_must_result_exists():
    assert RES.exists() and RES.stat().st_size > 0

def test_must_every_input_file_has_exactly_one_result_line():
    names = [LINE.match(l).group(1) for l in RES.read_text().splitlines() if l.strip() and LINE.match(l)]
    assert sorted(names) == sorted(EXPECTED), names

def test_must_winning_pattern_sets_correct():
    got = _parse()
    for f, exp in EXPECTED.items():
        if exp != {NO}: assert got.get(f) == exp, (f, got.get(f), exp)

def test_must_non_winning_hand_reported():
    assert _parse().get("hand_003.json") == {NO}

def test_mustnot_input_hands_modified():
    for f, md5 in INPUT_MD5.items():
        p = Path("/app") / f
        assert p.exists() and hashlib.md5(p.read_bytes()).hexdigest() == md5, f

def test_mustnot_extra_or_unknown_files_in_result():
    if not RES.exists(): pytest.skip("no output yet")
    assert set(_parse()) <= set(EXPECTED)

def test_untested_exact_line_format():
    # "{filename}: { "A", "B" }" -- brace-enclosed, quoted, comma-separated; official test only regex-extracts quotes
    fmt = re.compile(r'^hand_\d{3}\.json: \{ ?"[^"]+"(, ?"[^"]+")* ?\}$')
    for line in RES.read_text().splitlines():
        if line.strip(): assert fmt.match(line), repr(line)

def test_untested_pattern_labels_use_required_wording():
    allowed = {SP, ST, TO, NO}
    for f, s in _parse().items(): assert s <= allowed, (f, s)
