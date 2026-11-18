#!/usr/bin/env python3
"""Pre-build the test virtualenv of a task once, so test containers mount it instead of re-installing per snapshot.
   1. run run-tests.sh once in a pristine container; 2. copy the resulting .tbench-testing venv to E4_VENV_DIR/<task>/venv;
   3. validate: with the venv mounted read-only, tests on pristine + oracle must reproduce the calibration result.
   Writes E4_VENV_DIR/<task>/prebake.json {ok, path, reason}. Only ok=true venvs are ever mounted."""
import sys, os, json, time, shutil, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import e4_replay as R
task = sys.argv[1]
d = os.path.join(R.VENVS, task); os.makedirs(d, exist_ok=True)
meta = os.path.join(d, "prebake.json")
def done(ok, path=None, reason=""):
    json.dump({"task": task, "ok": ok, "path": path, "reason": reason, "when": time.time()}, open(meta, "w"), indent=1)
    print(f"[{task}] ok={ok} path={path} {reason}"); sys.exit(0)
if os.path.exists(meta) and json.load(open(meta)).get("ok"): print("exists", task); sys.exit(0)
os.environ["E4_NO_VENV"] = "1"          # build phase: never mount
t0 = time.time()
c = R.Container(task, f"{task}__prebake__x", "miniswe"); c.start()
try:
    r = R.sh(["docker", "exec", "-w", "/app", c.name, "bash", "-c", "TEST_DIR=/tests bash /tests/run-tests.sh > /tmp/prebake.log 2>&1; echo RC=$?"], timeout=R.TEST_TIMEOUT)
    path = R.sh(["docker", "exec", c.name, "bash", "-c", "find /app -maxdepth 3 -type d -name .tbench-testing | head -1"]).stdout.strip()
    if not path:
        done(False, None, "run-tests.sh creates no .tbench-testing venv (system python or other layout)")
    py = R.sh(["docker", "exec", c.name, "readlink", "-f", f"{path}/bin/python"]).stdout.strip()
    venv = os.path.join(d, "venv"); shutil.rmtree(venv, ignore_errors=True)
    R.sh(f"docker cp {c.name}:{path} {venv}", check=True)
finally:
    c.stop()
# validate with the mount on a fresh pristine container
del os.environ["E4_NO_VENV"]
json.dump({"task": task, "ok": True, "path": path, "reason": "validating", "when": time.time()}, open(meta, "w"))
c = R.Container(task, f"{task}__prebakeval__x", "miniswe"); c.start()
try:
    base = c.snapshot(0)
    pristine = R.Container.run_tests(base, False, task)
    oracle = R.Container.run_tests(base, True, task) if c.has_oracle else None
    R.Container.drop(base)
finally:
    c.stop()
cal = {}
cf = os.path.join(R.ROOT, "resub/e4/calib", f"{task}.json")
if os.path.exists(cf): cal = json.load(open(cf))
ok = bool(oracle) and oracle.get("total") and oracle["passed"] == oracle["total"]
if cal.get("oracle") and oracle: ok = ok or (oracle["passed"] == cal["oracle"].get("passed") and oracle["total"] == cal["oracle"].get("total"))
reason = f"pristine {pristine and pristine.get('passed')}/{pristine and pristine.get('total')} oracle {oracle and oracle.get('passed')}/{oracle and oracle.get('total')} python={py} {round(time.time()-t0)}s"
if not ok: shutil.rmtree(os.path.join(d, "venv"), ignore_errors=True)
done(bool(ok), path if ok else None, reason)
