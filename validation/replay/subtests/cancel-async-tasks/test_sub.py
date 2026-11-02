# E4 sub-tests for cancel-async-tasks. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import subprocess, signal, time, textwrap, pytest
from pathlib import Path
RUN = Path("/app/run.py")
PY = "python3"
PROBE = textwrap.dedent("""
    import asyncio, sys, time
    from run import run_tasks
    N, M, D = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    cur = peak = 0
    async def task():
        global cur, peak
        cur += 1; peak = max(peak, cur)
        try:
            print("started", flush=True); await asyncio.sleep(D); print("finished", flush=True)
        finally:
            cur -= 1; await asyncio.sleep(0.2); print("cleaned", flush=True)
    async def main():
        t0 = time.monotonic(); await run_tasks([task]*N, M); print("elapsed", round(time.monotonic()-t0, 3), "peak", peak, flush=True)
    asyncio.run(main())
""")

def _run(n, m, d, timeout=20):
    r = subprocess.run([PY, "-c", PROBE, str(n), str(m), str(d)], cwd="/app", capture_output=True, text=True, timeout=timeout)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout

def _sigint(n, m, d=3.0):
    p = subprocess.Popen([PY, "-c", PROBE, str(n), str(m), str(d)], cwd="/app", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.7); p.send_signal(signal.SIGINT)
    try: out, _ = p.communicate(timeout=10)
    finally: p.kill()
    return out.decode()

def _parse(out):
    kv = out.split("elapsed")[-1].split(); return float(kv[0]), int(kv[2])

def test_must_run_py_exports_async_run_tasks():
    assert RUN.exists()
    r = subprocess.run([PY, "-c", "import inspect; from run import run_tasks; assert inspect.iscoroutinefunction(run_tasks)"], cwd="/app", capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr[-800:]

def test_must_tasks_run_concurrently():
    out = _run(3, 3, 0.5); el, peak = _parse(out)
    assert out.count("cleaned") == 3 and peak == 3 and el < 1.2, out

def test_must_max_concurrent_respected():
    out = _run(4, 2, 0.4); el, peak = _parse(out)
    assert out.count("finished") == 4 and peak == 2 and el >= 1.2, out

def test_must_cleanup_runs_on_keyboard_interrupt():
    out = _sigint(2, 3); assert out.count("started") == 2 and out.count("cleaned") == 2, out

def test_must_interrupt_does_not_start_queued_tasks():
    out = _sigint(3, 2); assert out.count("started") == 2 and out.count("cleaned") == 2, out

def test_mustnot_import_has_side_effects():
    if not RUN.exists(): pytest.skip("no run.py yet")
    t0 = time.monotonic()
    r = subprocess.run([PY, "-c", "import run"], cwd="/app", capture_output=True, text=True, timeout=20)
    assert r.returncode == 0 and time.monotonic() - t0 < 5 and r.stdout.strip() == "", (r.stdout[-300:], r.stderr[-300:])

def test_mustnot_return_before_tasks_finish():
    if not RUN.exists(): pytest.skip("no run.py yet")
    out = _run(2, 2, 0.5); el, _ = _parse(out)
    assert out.index("elapsed") > out.rindex("cleaned") and el >= 0.7, out

def test_untested_exact_signature():
    # official tests call positionally; instruction fixes the parameter names (tasks, max_concurrent)
    code = "import inspect; from run import run_tasks; p=list(inspect.signature(run_tasks).parameters); assert p[:2]==['tasks','max_concurrent'], p"
    r = subprocess.run([PY, "-c", code], cwd="/app", capture_output=True, text=True, timeout=20); assert r.returncode == 0, r.stderr[-500:]
