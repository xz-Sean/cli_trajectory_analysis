#!/usr/bin/env python3
"""Calibrate sub-tests for a task: (a) pristine image must FAIL must-tests, (b) oracle must pass all
must/untested and violate no mustnot. PASS-trajectory finals are checked via e4_replay.py replay --kmin m --kmax m."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import e4_replay as R
task = sys.argv[1]
cid = f"{task}__calib__x"
c = R.Container(task, cid, "miniswe"); c.start()
try:
    base = c.snapshot(0)
    pristine = R.Container.run_tests(base, False)
    oracle = R.Container.run_tests(base, True) if c.has_oracle else None
    R.Container.drop(base)
finally:
    c.stop()
def fmt(r):
    if not r: return "n/a"
    s = r.get("sub", {})
    return f"official {r['passed']}/{r['total']} | must {s.get('must',{}).get('passed')}/{s.get('must',{}).get('total')} mustnot {s.get('mustnot',{}).get('passed')}/{s.get('mustnot',{}).get('total')} untested {s.get('untested',{}).get('passed')}/{s.get('untested',{}).get('total')} | oracle_rc={r.get('oracle_rc')}"
print(f"[{task}] pristine: {fmt(pristine)}")
print(f"[{task}] oracle  : {fmt(oracle)}")
out = {"task": task, "pristine": pristine, "oracle": oracle}
os.makedirs(R.OUT + "/../calib", exist_ok=True)
json.dump(out, open(os.path.join(R.OUT, "..", "calib", f"{task}.json"), "w"), indent=1)
