# E4 sub-tests for aimo-airline-departures. State assertions only.
import subprocess, re, os
from pathlib import Path
S = Path("/app/airline_analysis.py"); RES = Path("/app/results.txt")

def test_must_script_exists():
    assert S.exists() and S.stat().st_size > 0

def test_must_results_exists():
    assert RES.exists()

def test_must_results_is_79():
    assert re.search(r"\b79\b", RES.read_text())

def test_must_script_runs():
    r = subprocess.run(["python3", str(S)], capture_output=True, text=True, cwd="/app")
    assert r.returncode == 0, r.stderr[-800:]

# DROPPED after calibration (oracle fails them; see ../CALIBRATION_NOTES.md):
#   test_mustnot_results_hardcoded_without_script  -- oracle's solution.sh writes results.txt directly; airline_analysis.py does not regenerate it
#   test_untested_results_is_just_the_number       -- oracle's results.txt contains a full proof, not "just the number"
