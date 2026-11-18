# E4 sub-tests for train-fasttext. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# fasttext (fasttext-wheel) is provided by the official tests' venv, which is active when these run.
import hashlib, os, pytest
from pathlib import Path
MODEL = Path("/app/model.bin"); TEST = Path("/tests/private_test.txt")
DATA_MD5 = {"/app/data/train-00000-of-00001.parquet": "de58ec09456863ecc994edfe5fec80a1",
            "/app/data/test-00000-of-00001.parquet": "a0f7735674814e628a7ee8e54ac90c1c"}
YELP_LABELS = {f"__label__{i}" for i in range(5)}

def _model():
    import fasttext
    return fasttext.load_model(str(MODEL))

def test_must_model_bin_exists():
    assert MODEL.is_file() and MODEL.stat().st_size > 0

def test_must_model_under_150mb():
    assert MODEL.stat().st_size < 150 * 1024 * 1024, MODEL.stat().st_size

def test_must_model_loads_and_predicts():
    m = _model(); lab, prob = m.predict("the food was great and the staff were friendly")
    assert lab and lab[0].startswith("__label__"), lab

def test_must_accuracy_above_0_62_on_private_test():
    m = _model(); n = ok = 0
    with open(TEST, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) != 2: continue
            n += 1; ok += m.predict(parts[1])[0][0] == parts[0]
    assert n > 0 and ok / n > 0.62, (ok, n, ok / n)

def test_mustnot_data_files_modified():
    for p, md5 in DATA_MD5.items():
        assert os.path.isfile(p), p
        assert hashlib.md5(open(p, "rb").read()).hexdigest() == md5, p

def test_untested_model_labels_are_the_five_yelp_classes():
    # "train on the yelp data": a model trained on data/ has exactly the 5 star-rating labels
    if not MODEL.is_file(): pytest.skip("no model")
    assert set(_model().get_labels()) == YELP_LABELS, _model().get_labels()
