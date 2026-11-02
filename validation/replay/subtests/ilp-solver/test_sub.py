# E4 sub-tests for ilp-solver. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import re, subprocess, pytest
from pathlib import Path
OUT = Path("/app/ilp_output.txt")
EXPECTED = ["Invest A: y", "Invest B: n", "Defer B: n", "Invest C: y", "Maximized NPV: 299.00"]

def _lines():
    return [l.strip() for l in OUT.read_text().splitlines() if l.strip()]

def test_must_output_file_exists():
    assert OUT.exists() and OUT.stat().st_size > 0

def test_must_investment_decisions():
    ls = _lines()
    for want in EXPECTED[:4]: assert want in ls, (want, ls[-8:])

def test_must_maximized_npv_299():
    m = re.search(r"Maximized NPV:\s*([0-9.]+)", OUT.read_text()); assert m, "no NPV line"
    assert abs(float(m.group(1)) - 299.0) < 0.005

def test_mustnot_pyscipopt_removed():
    # the shipped solver lives in the system interpreter (/usr/bin/python3), not in the official tests' venv
    r = subprocess.run(["/usr/bin/python3", "-c", "import pyscipopt"], capture_output=True, text=True, timeout=50)
    assert r.returncode == 0, r.stderr[-500:]

def test_mustnot_contradictory_decision_lines():
    # each decision must appear exactly once (no 'Invest B: y' and 'Invest B: n' both present)
    if not OUT.exists(): pytest.skip("no output yet")
    txt = OUT.read_text()
    for key in ("Invest A:", "Invest B:", "Defer B:", "Invest C:", "Maximized NPV:"):
        assert len(re.findall(r"^\s*" + re.escape(key), txt, re.M)) == 1, key

def test_untested_five_lines_consecutive_and_in_order():
    # official test uses substring checks; instruction fixes the five-line format and order
    ls = _lines(); assert EXPECTED[0] in ls, ls[-8:]
    i = ls.index(EXPECTED[0]); assert ls[i:i+5] == EXPECTED, ls[i:i+5]

def test_untested_npv_two_decimal_places():
    m = re.search(r"Maximized NPV:\s*(\S+)", OUT.read_text()); assert m and re.fullmatch(r"\d+\.\d{2}", m.group(1)), m and m.group(1)

# REWRITTEN after calibration: test_untested_exact_format_and_order (assert _lines() == EXPECTED) was relaxed to the
# consecutive/in-order check above because the reference solution.sh pipes the SCIP solver log into /app/ilp_output.txt
# (via tee), so its file is NOT "in the following format" (reference solution violates the output-format requirement).
