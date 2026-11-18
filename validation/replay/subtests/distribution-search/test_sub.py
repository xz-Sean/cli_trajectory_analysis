# E4 sub-tests for distribution-search. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import subprocess, pytest
from pathlib import Path
DIST = Path("/app/dist.npy"); V = 150_000; TARGET = 10.0; TOL = 1e-3

def _P():
    import numpy as np
    if not DIST.exists(): pytest.fail("/app/dist.npy missing")
    return np.load(DIST)

def test_must_dist_file_exists_and_loads():
    assert DIST.is_file(); _P()

def test_must_vocab_size_150000():
    P = _P(); assert P.ndim == 1 and P.size == V, P.shape

def test_must_valid_probability_distribution():
    import numpy as np
    P = _P().astype(float)
    assert np.isfinite(P).all() and P.min() > 0 and P.max() <= 1.0, (P.min(), P.max())
    assert abs(P.sum() - 1.0) < 1e-5, P.sum()

def test_must_forward_kl_is_10():
    import numpy as np
    P = _P().astype(float); P = P / P.sum()
    kf = float(np.sum(P * np.log(P)) + np.log(P.size))
    assert abs(kf - TARGET) <= TOL, kf

def test_must_backward_kl_is_10():
    import numpy as np
    P = _P().astype(float); P = P / P.sum()
    kb = float(-np.log(P.size) - np.sum(np.log(P)) / P.size)
    assert abs(kb - TARGET) <= TOL, kb

def test_mustnot_dist_is_pickled_or_non_numeric():
    import numpy as np
    if not DIST.exists(): pytest.skip("no output yet")
    P = np.load(DIST, allow_pickle=False)      # a plain numeric .npy, not an object/pickle payload
    assert P.dtype.kind == "f", P.dtype

def test_mustnot_provided_numpy_scipy_removed():
    # "We provide numpy and scipy" -- the agent must not have broken the provided environment
    r = subprocess.run(["/usr/local/bin/python", "-c", "import numpy, scipy"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]

def test_untested_python_script_that_produces_dist_exists():
    # instruction: "Create a Python script that implements the following" -- official tests only inspect dist.npy
    scripts = [p for p in Path("/app").rglob("*.py") if ".tbench-testing" not in p.parts and "tests" not in p.parts]
    assert any("dist.npy" in p.read_text(errors="ignore") for p in scripts), "no /app/*.py script refers to dist.npy"
