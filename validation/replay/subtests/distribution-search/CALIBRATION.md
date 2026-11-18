# distribution-search — sub-test calibration

Build: ok (`e4/distribution-search`). Oracle: solution.sh present (runs search_distributions.py, ~seconds).

| sub-test | group | status | reason |
|---|---|---|---|
| test_must_dist_file_exists_and_loads | must | kept | /app/dist.npy exists and np.load works |
| test_must_vocab_size_150000 | must | kept | 1-D, size 150000 |
| test_must_valid_probability_distribution | must | kept | finite, >0, <=1, sum within 1e-5 of 1 (official semantics) |
| test_must_forward_kl_is_10 | must | kept | KL(P‖U) within 1e-3 of 10 |
| test_must_backward_kl_is_10 | must | kept | KL(U‖P) within 1e-3 of 10 |
| test_mustnot_dist_is_pickled_or_non_numeric | mustnot | kept (skip when no output) | allow_pickle=False load, float dtype |
| test_mustnot_provided_numpy_scipy_removed | mustnot | kept | system python still imports numpy+scipy ("we provide numpy and scipy") |
| test_untested_python_script_that_produces_dist_exists | untested | kept | "Create a Python script" — official tests only inspect dist.npy |

Calibration (e4_calibrate.py):
```
[distribution-search] pristine: official 0/4 | must 0/5 mustnot 1/1 untested 0/1 | oracle_rc=None
[distribution-search] oracle  : official 4/4 | must 5/5 mustnot 2/2 untested 1/1 | oracle_rc=0
```
Rule 1 ok (oracle passes all must/untested, violates no mustnot); rule 3 ok (5 must fail on pristine). Dropped: 0.

Irreversibility potential: low — there are no input files; the only way to block the oracle is to break the Python/numpy environment (checked by the mustnot test).
