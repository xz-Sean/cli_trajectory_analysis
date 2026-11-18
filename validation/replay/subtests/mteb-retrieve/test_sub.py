# E4 sub-tests for mteb-retrieve. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import hashlib, os, glob, pytest
from pathlib import Path
RES = Path("/app/result.txt"); DATA = Path("/app/data.txt")
DATA_MD5 = "ca4f42e6a1cde83d719d489a7ecaee7c"   # md5 of task-deps/data.txt as shipped by the Dockerfile COPY
EXPECTED = "MTEB: Massive Text Embedding Benchmark"

def test_must_result_exists():
    assert RES.exists() and RES.stat().st_size > 0

def test_must_result_single_line():
    assert len(RES.read_text().splitlines()) == 1

def test_must_result_is_5th_most_similar_doc():
    assert RES.read_text().strip() == EXPECTED

def test_must_result_is_a_verbatim_line_of_data():
    # "write the resulting line": the content must be exactly one of the documents in data.txt
    docs = [l.strip() for l in DATA.read_text().splitlines()]
    assert RES.read_text().strip() in docs

def test_mustnot_data_txt_modified():
    assert DATA.exists() and hashlib.md5(DATA.read_bytes()).hexdigest() == DATA_MD5

def test_mustnot_result_is_a_directory_or_multiple_docs():
    if not RES.exists(): pytest.skip("no output yet")
    assert RES.is_file()
    assert len([l for l in RES.read_text().splitlines() if l.strip()]) == 1

def test_untested_specified_model_revision_was_used():
    # instruction pins bge-small-zh-v1.5 @ 7999e1d...; the only end-state evidence is the HF snapshot cache
    roots = {os.environ.get("HF_HOME", ""), os.environ.get("HF_HUB_CACHE", ""), "/root/.cache/huggingface", "/app", "/root"}
    hits = []
    for r in filter(None, roots):
        hits += glob.glob(os.path.join(r, "**", "models--BAAI--bge-small-zh-v1.5", "snapshots", "7999e1d3359715c523056ef9478215996d62a620"), recursive=True)
    assert hits, "no cached snapshot of BAAI/bge-small-zh-v1.5 @ 7999e1d… found"
