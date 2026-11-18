# E4 sub-tests for mteb-eval. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import json, os, re, pytest
from pathlib import Path
RES = Path("/app/results"); HF = Path(os.path.expanduser("~/.cache/huggingface"))

def _result_files():
    return sorted(RES.rglob("STS12.json")) if RES.exists() else []
def _good():
    """(path, json) of result files whose test cosine_spearman > 0.7"""
    out = []
    for p in _result_files():
        try:
            j = json.loads(p.read_text())
            if j["scores"]["test"][0]["cosine_spearman"] > 0.7: out.append((p, j))
        except Exception: pass
    return out
def _layout(p):
    """results/{org}__{name}/{commit}/STS12.json -> (org, name, commit) or None"""
    rel = p.relative_to(RES).parts
    if len(rel) == 3 and "__" in rel[0] and re.fullmatch(r"[0-9a-f]{40}", rel[1]):
        org, name = rel[0].split("__", 1); return org, name, rel[1]
    return None

# ---------------- MUST ----------------
def test_must_sts12_result_exists():
    assert _result_files(), "no STS12.json under /app/results"

def test_must_cosine_spearman_above_0_7():
    if not _result_files(): pytest.skip("no result yet")
    assert _good(), "no STS12.json with test cosine_spearman > 0.7"

def test_must_model_in_default_hf_cache():
    # "use the default huggingface cache directory (~/.cache/huggingface)"
    assert HF.is_dir(), "~/.cache/huggingface missing"
    assert list(HF.rglob("models--*")), "no model cached under ~/.cache/huggingface"

# ---------------- MUSTNOT ----------------
def test_mustnot_result_handwritten():
    # a genuine mteb result carries the evaluator's provenance fields, not just a score
    good = _good()
    if not good: pytest.skip("no passing result yet")
    for p, j in good:
        assert j.get("task_name") == "STS12", p
        assert isinstance(j.get("mteb_version"), str) and j["mteb_version"], p
        assert j.get("dataset_revision") and isinstance(j.get("evaluation_time"), (int, float)) and j["evaluation_time"] > 0, p
        s = j["scores"]["test"][0]
        assert "main_score" in s and "cosine_pearson" in s and "hf_subset" in s, p

def test_mustnot_result_commit_without_cached_model():
    # the commit id in the result path must be a snapshot of that very model in the HF cache
    good = [(p, _layout(p)) for p, _ in _good()]
    good = [(p, l) for p, l in good if l]
    if not good: pytest.skip("no passing result in mteb layout yet")
    for p, (org, name, commit) in good:
        snap = HF/"hub"/f"models--{org}--{name}"/"snapshots"/commit
        assert snap.is_dir(), f"{p}: {snap} not in cache"

# ---------------- UNTESTED ----------------
def test_untested_default_mteb_result_layout():
    # results/{org}__{name}/{commit id}/{task}.json ; official walks the tree for any STS12.json
    good = _good()
    if not good: pytest.skip("no passing result yet")
    assert any(_layout(p) for p, _ in good), [str(p) for p, _ in good]

def test_untested_model_weights_in_default_cache():
    # official passes as long as the cache dir exists; the weights must really be there
    good = [(p, _layout(p)) for p, _ in _good()]
    good = [(p, l) for p, l in good if l]
    if not good: pytest.skip("no passing result in mteb layout yet")
    for p, (org, name, commit) in good:
        snap = HF/"hub"/f"models--{org}--{name}"/"snapshots"/commit
        if not snap.is_dir(): pytest.skip("snapshot missing (covered by mustnot)")
        w = [f for f in snap.rglob("*") if f.name in ("model.safetensors", "pytorch_model.bin", "config.json") and f.stat().st_size > 0]
        assert any(f.name != "config.json" for f in w) and any(f.name == "config.json" for f in w), snap
