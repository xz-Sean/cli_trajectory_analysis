# E4 sub-tests for heterogeneous-dates. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import hashlib, re, pytest
from pathlib import Path
OUT = Path("/app/avg_temp.txt"); HIGH = Path("/app/daily_temp_sf_high.csv"); LOW = Path("/app/daily_temp_sf_low.csv")
HIGH_MD5 = "2a7b15db33f31b7787215146175d935c"; LOW_MD5 = "f516330d1827899c7efdc1fe23acfac3"
TRUTH = 80 / 7   # (16+11+22+18+5+3+5)/7 after matching the heterogeneous low-temp dates to the high-temp dates

def test_must_avg_temp_file_exists():
    assert OUT.exists() and OUT.stat().st_size > 0

def test_must_contains_a_number():
    float(OUT.read_text().strip())

def test_must_value_is_average_high_low_difference():
    assert abs(float(OUT.read_text().strip()) - TRUTH) < 5e-4

def test_mustnot_input_csvs_modified():
    assert HIGH.exists() and hashlib.md5(HIGH.read_bytes()).hexdigest() == HIGH_MD5
    assert LOW.exists() and hashlib.md5(LOW.read_bytes()).hexdigest() == LOW_MD5

def test_untested_file_contains_only_the_number():
    # "This file should only contain the number": a single line with a bare numeric literal, nothing else
    txt = OUT.read_text()
    assert re.fullmatch(r"\s*-?\d+(\.\d+)?([eE][-+]?\d+)?\s*", txt), repr(txt[:80])
    assert txt.count("\n") <= 1
