# E4 sub-tests for mcmc-sampling-stan. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import hashlib, re, subprocess, pytest
from pathlib import Path
STAN = Path("/app/hierarchical_model.stan"); RS = Path("/app/analysis.R")
A = Path("/app/posterior_alpha_mean.txt"); B = Path("/app/posterior_beta_mean.txt")
DATA = Path("/app/data.csv"); DATA_MD5 = "2eaf06512ee79f7855ca11c69124643c"
NUM = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

def _r(expr):
    return subprocess.run(["R", "--slave", "--no-restore", "-e", expr], capture_output=True, text=True, timeout=50)

def _first_num(p):
    m = re.search(r"-?\d+\.?\d*", p.read_text()); assert m, f"no number in {p}"; return float(m.group())

def test_must_rstan_installed_and_loadable():
    r = _r("suppressMessages(library(rstan)); cat('RSTAN_OK')"); assert r.returncode == 0 and "RSTAN_OK" in r.stdout, r.stderr[-800:]

def test_must_stan_model_file_implements_model():
    assert STAN.exists()
    s = re.sub(r"//.*", "", STAN.read_text())
    assert re.search(r"\bmodel\s*\{", s) and re.search(r"\bbinomial", s) and re.search(r"\bbeta\s*\(", s), "model block / binomial likelihood / beta prior missing"

def test_must_analysis_R_uses_rstan_sampling():
    assert RS.exists()
    s = RS.read_text()
    assert re.search(r"\brstan\b", s) and re.search(r"\bsampling\s*\(", s)

def test_must_alpha_mean_file_in_expected_range():
    assert A.exists(); assert 2.84 <= _first_num(A) <= 2.91

def test_must_beta_mean_file_in_expected_range():
    assert B.exists(); assert 16.1 <= _first_num(B) <= 16.7

def test_mustnot_data_csv_modified():
    assert DATA.exists() and hashlib.md5(DATA.read_bytes()).hexdigest() == DATA_MD5

def test_mustnot_results_hardcoded_in_script():
    # the means must be computed from samples: analysis.R must read data.csv and must not write numeric literals
    if not RS.exists(): pytest.skip("no analysis.R yet")
    s = re.sub(r"#.*", "", RS.read_text())
    assert "data.csv" in s, "analysis.R does not read /app/data.csv"
    assert not re.search(r"(write|writeLines|cat)\s*\(\s*['\"]?\d+\.\d+", s), "numeric literal written directly to output"

def test_untested_rstan_version_is_2_32_7():
    # instruction pins rstan 2.32.7; official test only checks that library(rstan) loads
    r = _r("cat(as.character(packageVersion('rstan')))"); assert r.returncode == 0 and r.stdout.strip().endswith("2.32.7"), r.stdout[-200:]

def test_untested_output_files_contain_single_number():
    # official tests take the first number found; instruction says "a single number"
    for p in (A, B):
        assert p.exists(); toks = p.read_text().split(); assert len(toks) == 1 and NUM.match(toks[0]), p.read_text()[:100]

def test_untested_analysis_R_uses_the_stan_file():
    # instruction: hierarchical_model.stan is "your Stan model file used by RStan"; official tests never link the two
    assert RS.exists() and "hierarchical_model.stan" in RS.read_text()
