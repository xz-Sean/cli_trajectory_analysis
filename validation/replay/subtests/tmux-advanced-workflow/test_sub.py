# E4 sub-tests for tmux-advanced-workflow. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# NOTE: tmux session/pane state is a live process and does not survive the snapshot (docker commit) used by the
# harness, so only on-disk effects of the workflow are asserted.
import hashlib, os, shutil, subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
P = Path("/app/project"); SCRIPT = P/"src/process_data.py"; OUT = P/"data/output.csv"; LOG = P/"logs/process.log"
MD5 = {"data/input.csv": "673114a67bb3af8c921464676e20f3ce", "src/monitor.py": "edf58110539b78c7622d7a7de9a75c4a"}

def _check_csv(lines):
    assert len(lines) == 9, len(lines)
    for ln in lines:
        assert ln.count("\n") == 1 and not ln.endswith("\n\n"), repr(ln)
        parts = ln.rstrip("\n").split(",")
        assert len(parts) == 4, parts; float(parts[2])

def test_must_process_script_bug_fixed():
    # run a copy of the script from a scratch tree (it logs to <script dir>/../logs/process.log) so the
    # real project log is not touched by this test
    with TemporaryDirectory() as d:
        os.makedirs(f"{d}/src"); os.makedirs(f"{d}/logs"); shutil.copy2(SCRIPT, f"{d}/src/process_data.py")
        r = subprocess.run(["python", f"{d}/src/process_data.py", str(P/"data/input.csv"), f"{d}/o.csv"],
                           capture_output=True, text=True, timeout=50)
        assert r.returncode == 0, r.stderr[-800:]
        _check_csv(open(f"{d}/o.csv").readlines())

def test_must_log_shows_processing_runs():
    # steps 3 and 5 run the script twice; the official test_bug_fixed adds exactly one more "Starting" entry
    # before these sub-tests run, so >= 2 means the agent ran it at least once (pristine+official = 1)
    t = LOG.read_text()
    assert t.count("Starting processing") >= 2, t[-800:]

# DROPPED after calibration (oracle fails it):
#   test_must_output_csv_produced_by_fixed_script  -- asserted /app/project/data/output.csv exists with 9 clean rows
#   (instruction steps 3/5/6). The reference solution.sh waits only 2 s per run while process_data.py sleeps 5 s, then
#   kills the tmux session, so its processing runs never finish and output.csv is never written. Observation: the
#   reference solution does not satisfy steps 3, 5 and 6, and the official tests never look at output.csv.

def test_mustnot_input_or_monitor_modified():
    for rel, md5 in MD5.items():
        f = P/rel; assert f.is_file(), rel
        assert hashlib.md5(f.read_bytes()).hexdigest() == md5, rel

def test_mustnot_scripts_lose_exec_bit():
    assert os.access(SCRIPT, os.X_OK) and os.access(P/"src/monitor.py", os.X_OK)

def test_untested_fix_is_strip_on_split():
    # hint in the instruction: missing strip() when splitting lines
    src = SCRIPT.read_text()
    assert "strip()" in src and "line.split(',')" not in src.replace("line.strip().split(',')", ""), src[-600:]

# UNTESTED (infeasible as end-state): tmux session "workflow" with 3 panes, monitor.py in the top pane, less in the
# bottom-left pane -- live tmux processes are not captured by the snapshot; the reference solution itself kills the
# session at the end (tmux kill-session -t workflow).
