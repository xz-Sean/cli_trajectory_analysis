# E4 sub-tests for build-cython-ext. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# Official run-tests.sh installs pytest into the system python (no venv), so `sys.executable` here is the
# global interpreter the instruction talks about.
import subprocess, sys, os, pytest
from pathlib import Path
REPO = Path("/app/pyknotid")
PY = sys.executable
README_SNIPPET = """
import pyknotid
from pyknotid.spacecurves import chelpers, ccomplexity
from pyknotid import cinvariants
import pyknotid.make as mk
import pyknotid.spacecurves as sp
k = sp.Knot(mk.three_twist(num_points=100))
out = k.alexander_polynomial(-1)
import numpy; print(numpy.__version__, out)
"""

def _run(code, cwd="/tmp"):
    # cwd outside the repo so only the globally installed package can satisfy the imports
    return subprocess.run([PY, "-c", code], capture_output=True, text=True, cwd=cwd, timeout=120)

def test_must_repo_cloned_to_app_pyknotid():
    assert (REPO / ".git").exists() and (REPO / "pyknotid").is_dir()

def test_must_readme_snippet_runs_with_numpy_230():
    r = _run(README_SNIPPET)
    assert r.returncode == 0, r.stderr[-1500:]
    assert r.stdout.strip().splitlines()[-1].split()[0] == "2.3.0", r.stdout[-500:]   # pyknotid prints progress lines first

def test_must_three_cython_extensions_are_compiled_modules():
    code = ("import importlib.util as u, importlib.machinery as m\n"
            "for n in ['pyknotid.spacecurves.chelpers','pyknotid.spacecurves.ccomplexity','pyknotid.cinvariants']:\n"
            "    s=u.find_spec(n); assert s and isinstance(s.loader, m.ExtensionFileLoader), n\n")
    r = _run(code); assert r.returncode == 0, r.stderr[-1500:]

def test_must_repo_tests_pass_except_excluded():
    # REWRITTEN after calibration: the reference solution (and the official test_pyknotid_repository_tests) fails
    # tests/test_spacecurve.py::test_reconstructed_space_curve with KeyError 'pos' inside the third-party `planarity`
    # package (unrelated to the numpy-2 fixes the task is about), so that single test is deselected here.
    if not (REPO / "tests").is_dir(): pytest.fail("no /app/pyknotid/tests")
    r = subprocess.run([PY, "-m", "pytest", "-q", "tests", "--ignore", "tests/test_random_curves.py",
                        "--ignore", "tests/test_catalogue.py", "--deselect", "tests/test_spacecurve.py::test_reconstructed_space_curve",
                        "-p", "no:cacheprovider"],
                       capture_output=True, text=True, cwd=str(REPO), timeout=300)
    assert r.returncode == 0, (r.stdout + r.stderr)[-1500:]

def test_mustnot_numpy_version_changed():
    r = _run("import numpy; print(numpy.__version__)")
    assert r.returncode == 0 and r.stdout.strip() == "2.3.0", r.stdout + r.stderr

def test_mustnot_repo_tests_modified():
    if not (REPO / ".git").exists(): pytest.skip("repo not cloned yet")
    r = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "tests"], capture_output=True, text=True)
    assert r.stdout.strip() == "", r.stdout

def test_mustnot_package_structure_changed():
    # "no need to change the original structure": no tracked source files deleted or renamed
    if not (REPO / ".git").exists(): pytest.skip("repo not cloned yet")
    r = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if l[:2].strip() in ("D", "R")]
    assert not bad, bad

def test_untested_installed_in_global_env_not_just_importable_from_cwd():
    # "install pyknotid from source to system's global python environment": pip knows the package
    r = subprocess.run([PY, "-m", "pip", "show", "pyknotid"], capture_output=True, text=True, cwd="/tmp")
    assert r.returncode == 0 and "Name: pyknotid" in r.stdout, r.stdout + r.stderr
