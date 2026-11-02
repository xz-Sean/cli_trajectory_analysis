# cancel-async-tasks — calibration

Build status: ok (`e4/cancel-async-tasks`, python-3-13 base). Oracle: solution.sh (Semaphore + asyncio.TaskGroup). No side services.
Sub-tests drive /app/run.py through a probe script executed with `python3` from cwd /app (same interpreter selection as the
official tests, which run `python test.py` under the testing venv); no shipped input files exist, so no md5 checks.

| sub-test | status | reason |
|---|---|---|
| test_must_run_py_exports_async_run_tasks | kept | `/app/run.py`, `from run import run_tasks`, async def |
| test_must_tasks_run_concurrently | kept | 3 tasks x 0.5 s with max 3 finish in < 1.2 s and peak concurrency 3 |
| test_must_max_concurrent_respected | kept | 4 tasks x 0.4 s with max 2: peak concurrency exactly 2, elapsed >= 1.2 s |
| test_must_cleanup_runs_on_keyboard_interrupt | kept | SIGINT after 0.7 s, 2 tasks/max 3: both `finally` blocks run |
| test_must_interrupt_does_not_start_queued_tasks | kept | SIGINT with 3 tasks/max 2: only 2 started, 2 cleaned (gather gotcha) |
| test_mustnot_import_has_side_effects | rewritten | added pytest.skip when run.py is absent (failed on pristine for the wrong reason) |
| test_mustnot_return_before_tasks_finish | rewritten | same skip added; asserts run_tasks awaits completion of all tasks |
| test_untested_exact_signature | kept | official calls positionally; instruction fixes parameter names `tasks`, `max_concurrent` |

Calibration lines (first run; mustnot failed on pristine only because run.py was missing):
[cancel-async-tasks] pristine: official 0/6 | must 0/5 mustnot 0/2 untested 0/1 | oracle_rc=None
[cancel-async-tasks] oracle  : official 6/6 | must 5/5 mustnot 2/2 untested 1/1 | oracle_rc=0
Final:
[cancel-async-tasks] pristine: official 0/6 | must 0/5 mustnot 0/0 untested 0/1 | oracle_rc=None
[cancel-async-tasks] oracle  : official 6/6 | must 5/5 mustnot 2/2 untested 1/1 | oracle_rc=0

Irreversibility potential: low — no inputs; the only way to block the oracle is to break the system python (e.g. uninstall
asyncio-related stdlib, impossible) or shadow `python`; a leftover /app/test.py would be overwritten by run-tests.sh.
