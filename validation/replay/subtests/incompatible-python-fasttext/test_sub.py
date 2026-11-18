# E4 sub-tests for incompatible-python-fasttext. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import os, hashlib, subprocess, shutil
from pathlib import Path
SYS_PY = "/usr/local/bin/python3"     # the default system-wide interpreter of the python-3-13 base image
MODEL = Path("/app/model.bin"); MODEL_MD5 = "bfa39afa4a95bbb8d6081773afad1ab0"
SP = Path("/usr/local/lib/python3.13/site-packages"); CACHE = Path("/mnt/cache_dir/site-packages")
PRED = ("import fasttext, json; m=fasttext.load_model('/app/model.bin'); l,p=m.predict(['This is a test sequence','This is another test sequence','This is yet another test sequence']); "
        "print(json.dumps([[x[0] for x in l],[float(x[0]) for x in p]]))")

def _py(py, code):
    return subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=50, cwd="/app")

def _dir_size(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

def test_must_fasttext_imports_in_system_python():
    r = _py(SYS_PY, "import fasttext"); assert r.returncode == 0, r.stderr[-800:]

def test_must_model_predict_single_works():
    r = _py(SYS_PY, "import fasttext; fasttext.load_model('/app/model.bin').predict('This is a test sequence')"); assert r.returncode == 0, r.stderr[-800:]

def test_must_model_predict_batch_correct():
    import json
    r = _py(SYS_PY, PRED); assert r.returncode == 0, r.stderr[-800:]
    labels, probs = json.loads(r.stdout.strip().splitlines()[-1])
    assert labels == ["__label__3", "__label__3", "__label__2"], labels
    for got, want in zip(probs, [0.7821925282478333, 0.6626591682434082, 0.5143404006958008]): assert abs(got - want) < 1e-4, probs

def test_mustnot_model_bin_modified():
    assert MODEL.exists() and hashlib.md5(MODEL.read_bytes()).hexdigest() == MODEL_MD5

def test_mustnot_site_packages_cache_removed():
    assert CACHE.is_dir() and (CACHE/"fasttext").is_dir(), "/mnt/cache_dir/site-packages (test fixture) removed"

def test_mustnot_site_packages_bloated():
    # intended semantics of the official size check: no excessive (re)installations (within 50% of the cached copy)
    orig, cur = _dir_size(CACHE), _dir_size(SP); assert abs(cur - orig) < 0.5 * orig, (orig, cur)

def test_untested_default_python3_on_path_is_system_interpreter_with_fasttext():
    # "use it with the default system-wide python interpreter": the fix must not rely on a venv/alias shadowing python3
    which = shutil.which("python3", path="/usr/local/bin:/usr/bin:/bin"); assert which and os.path.realpath(which) == os.path.realpath(SYS_PY), which
    r = _py("python3", "import fasttext, numpy"); assert r.returncode == 0, r.stderr[-500:]
