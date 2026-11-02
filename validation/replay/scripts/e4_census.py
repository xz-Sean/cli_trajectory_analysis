#!/usr/bin/env python3
"""E4 census driver: every replayable FAIL trajectory (miniswe+terminus2, in corpus_RPO) not yet replayed.
  prepare <task>     build image (if missing) + pristine/oracle calibration -> resub/e4/calib/<task>.json
  status             summarise task readiness -> resub/e4/census_tasks.json
  cases [--all]      emit resub/e4/census_cases.json (cid,kmin,kmax) for ready tasks, calibrated-first
"""
import json, os, sys, glob, subprocess, time
sys.path.insert(0, os.path.dirname(__file__))
import e4_replay as R
ROOT = R.ROOT; E4 = os.path.join(ROOT, "resub/e4")
TODO = json.load(open(os.path.join(E4, "census_todo_raw.json")))
EXC = json.load(open(os.path.join(E4, "exclusions.json")))
EXT = set(EXC["excluded_tasks"]); DROP = set(EXC.get("dropped_cids", []))

def image_exists(task):
    return subprocess.run(["docker", "image", "inspect", R.image_name(task)], capture_output=True).returncode == 0

def prepare(task):
    out = os.path.join(E4, "calib", f"{task}.json")
    if os.path.exists(out):
        print("calib exists", task); return
    t0 = time.time()
    if not image_exists(task):
        try: R.build(task)
        except SystemExit as e:
            json.dump({"task": task, "build_failed": str(e), "secs": time.time()-t0}, open(out, "w"), indent=1); print("BUILD FAILED", task); return
    c = R.Container(task, f"{task}__calib__x", "miniswe"); c.start()
    try:
        base = c.snapshot(0)
        pristine = R.Container.run_tests(base, False)
        oracle = R.Container.run_tests(base, True) if c.has_oracle else None
        R.Container.drop(base)
    finally:
        c.stop()
    json.dump({"task": task, "pristine": pristine, "oracle": oracle, "secs": round(time.time()-t0)}, open(out, "w"), indent=1)
    print(f"[{task}] pristine {pristine and pristine['passed']}/{pristine and pristine['total']} oracle {oracle and oracle['passed']}/{oracle and oracle['total']} rc={oracle and oracle.get('oracle_rc')} {round(time.time()-t0)}s")

def task_status(task):
    if task in EXT: return "excluded", EXC["reasons"].get(task, "")
    if os.path.isdir(os.path.join(E4, "subtests", task)): return "ready", "vetted in sample phase (per-run baseline oracle check applies)"
    f = os.path.join(E4, "calib", f"{task}.json")
    if not os.path.exists(f): return "pending", ""
    d = json.load(open(f))
    if d.get("build_failed"): return "excluded", "image build failed"
    o = d.get("oracle")
    if not o or not o.get("total"): return "excluded", "oracle/tests produced no result on pristine image"
    if o["passed"] < o["total"]: return "excluded", f"reference solution fails official tests on pristine image ({o['passed']}/{o['total']})"
    p = d.get("pristine") or {}
    if p.get("total") and p["passed"] == p["total"]: return "excluded", "official tests already pass on pristine image"
    return "ready", ""

def status():
    tasks = sorted({p["task"] for p in TODO})
    res = {t: dict(zip(("status", "reason"), task_status(t))) for t in tasks}
    for t in tasks: res[t]["n_traj"] = sum(1 for p in TODO if p["task"] == t)
    json.dump(res, open(os.path.join(E4, "census_tasks.json"), "w"), indent=1)
    from collections import Counter
    c = Counter(v["status"] for v in res.values()); n = Counter()
    for v in res.values(): n[v["status"]] += v["n_traj"]
    print("tasks", dict(c), "trajectories", dict(n))
    return res

def cases(all_pending=False):
    st = status(); have_sub = set(os.listdir(os.path.join(E4, "subtests")))
    rows = []
    for p in TODO:
        if p["cid"] in DROP: continue
        s = st[p["task"]]["status"]
        if s == "excluded": continue
        if s == "pending" and not all_pending: continue
        kmin = max(1, p["t_err"] - 1); kmax = min(p["m"], p["t_lock"] + 5)
        rows.append({"cid": p["cid"], "task": p["task"], "kmin": kmin, "kmax": kmax, "points": kmax - kmin + 1,
                     "has_subtests": p["task"] in have_sub, "status": s})
    rows.sort(key=lambda r: (0 if r["has_subtests"] else 1, r["points"]))
    json.dump(rows, open(os.path.join(E4, "census_cases.json"), "w"), indent=1)
    print(len(rows), "cases,", sum(r["points"] for r in rows), "points;", sum(r["has_subtests"] for r in rows), "with subtests")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prepare": prepare(sys.argv[2])
    elif cmd == "status": status()
    elif cmd == "cases": cases("--all" in sys.argv)
