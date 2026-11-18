# E4 sub-tests for puzzle-solver. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# Reference values below were computed by an independent BFS on the shipped start.txt/goal.txt:
# optimal length 30; frontier sizes per depth 0..30 as listed.
import csv, hashlib, pytest
from pathlib import Path
APP = Path("/app"); PATH = APP / "path.tsv"; LAYERS = APP / "layers.csv"
ORIG_MD5 = {"start.txt": "6a605c7c59267463033375c2a3f6fdb6", "goal.txt": "662399f93c2fc7df5b15dd753dee0add",
            "puzzle_solver_utils.py": "ee0c95e85869b0e36fc2fcb8d2f0db5f"}
OPT = 30
COUNTS = [1, 3, 5, 10, 14, 28, 42, 80, 108, 202, 278, 524, 726, 1348, 1804, 3283, 4193, 7322, 8596, 13930, 14713,
          21721, 19827, 25132, 18197, 18978, 9929, 7359, 2081, 878, 126]

def _grid(name):
    return [int(x) for ln in (APP / name).read_text().splitlines() for x in ln.split()]

def _key(t): return "".join(f"{x:02d}" for x in t)

def _rows():
    if not PATH.exists(): pytest.fail("path.tsv missing")
    with PATH.open() as f: return list(csv.DictReader(f, delimiter="\t"))

def _layers():
    if not LAYERS.exists(): pytest.fail("layers.csv missing")
    with LAYERS.open() as f: return [(int(r["depth"]), int(r["count"])) for r in csv.DictReader(f)]

def test_must_path_tsv_format():
    rows = _rows(); assert rows, "path.tsv has no moves"
    for i, r in enumerate(rows):
        assert int(r["step"]) == i and 1 <= int(r["tile"]) <= 8, r
        k = r["state_key"]; assert len(k) == 18 and sorted(k[j:j + 2] for j in range(0, 18, 2)) == [f"{x:02d}" for x in range(9)], k

def test_must_path_moves_legal_and_reach_goal():
    cur = _grid("start.txt"); goal = _key(_grid("goal.txt"))
    for r in _rows():
        b = cur.index(0); p = cur.index(int(r["tile"]))
        assert abs(b // 3 - p // 3) + abs(b % 3 - p % 3) == 1, f"step {r['step']}: tile {r['tile']} not adjacent to blank"
        cur[b], cur[p] = cur[p], cur[b]
        assert _key(cur) == r["state_key"], f"step {r['step']}: state_key does not follow from the move"
    assert _key(cur) == goal, "path does not end at the goal"

def test_must_path_is_optimal():
    assert len(_rows()) == OPT, f"path has {len(_rows())} moves, optimal is {OPT}"

def test_must_layers_csv_matches_bfs_frontier_sizes():
    lay = _layers(); assert lay == list(enumerate(COUNTS)), f"layers.csv rows differ from BFS frontier sizes (got {lay[:5]}...)"

def test_must_layer_files_with_matching_sha():
    start, goal = _key(_grid("start.txt")), _key(_grid("goal.txt"))
    for d, n in _layers():
        t, s = APP / f"L{d}.txt", APP / f"L{d}.sha"
        assert t.exists() and s.exists(), f"L{d}.txt / L{d}.sha missing"
        assert hashlib.sha256(t.read_bytes()).hexdigest() == s.read_text().strip(), f"L{d}.sha does not match L{d}.txt"
        states = [ln for ln in t.read_text().splitlines() if ln]
        assert len(states) == n == len(set(states)), f"L{d}.txt has {len(states)} states, layers.csv says {n}"
        if d == 0: assert states == [start]
        if d == OPT: assert goal in states

def test_mustnot_input_files_modified():
    for f, h in ORIG_MD5.items():
        assert (APP / f).exists(), f"{f} deleted"
        assert hashlib.md5((APP / f).read_bytes()).hexdigest() == h, f"{f} modified"

def test_mustnot_total_states_exceed_9_factorial():
    if not LAYERS.exists(): pytest.skip("no output yet")
    assert sum(n for _, n in _layers()) <= 362880

def test_untested_header_column_order():
    # instruction fixes the column order "step,tile,state_key" / "depth,count"; official tests compare header sets only
    assert PATH.read_text().splitlines()[0] == "step\ttile\tstate_key"
    assert LAYERS.read_text().splitlines()[0] == "depth,count"

# DROPPED (rule 1, checked against the oracle before calibration):
#   test_untested_solver_script_exists -- instruction: "Create a system that solves an 8-puzzle"; the reference solution runs its
#   BFS from inline heredocs and leaves no solver script in /app, so a "solver script exists" assertion cannot be calibrated.
