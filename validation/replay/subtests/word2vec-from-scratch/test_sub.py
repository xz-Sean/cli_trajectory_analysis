# E4 sub-tests for word2vec-from-scratch. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import os, pickle, hashlib, importlib, dataclasses, pytest
from pathlib import Path
MODEL = Path("/app/model.pt"); VOCAB = Path("/app/vocab.pkl")
TRAIN = Path("/app/wikitext-data/train.txt"); VAL = Path("/app/wikitext-data/validation.txt")
# wikitext-2-v1 files are generated at image build time (not COPY'd) and the e4 image build fails (HF hub bit-rot),
# so no md5 could be taken; wikitext-2-v1 row counts (train 36718, validation 3760) are asserted instead.
TRAIN_LINES = 36718; VAL_LINES = 3760
REQUIRED = ["man","woman","king","queen","girl","prince","boy","father","mother","son","daughter","brother","sister",
            "america","france","england","germany","japan","china","paris","london","good","bad","big","small"]

@dataclasses.dataclass
class Vocab:
    word_to_idx: dict
    idx_to_word: list

class _Rec(pickle.Unpickler):
    """returns our Vocab for any class whose attrs we need, but records the pickled (module, name)"""
    seen = None
    def find_class(self, module, name):
        if name == "Vocab" or self.seen is None and module not in ("builtins", "collections", "dataclasses", "copyreg", "_codecs"):
            _Rec.seen = (module, name); return Vocab
        return super().find_class(module, name)

def _vocab():
    _Rec.seen = None
    with open(VOCAB, "rb") as f: return _Rec(f).load()

def _emb():
    import torch
    sd = torch.load(MODEL, map_location="cpu")
    assert isinstance(sd, dict) and "embeddings.weight" in sd, "model.pt must be a state dict with 'embeddings.weight'"
    return sd["embeddings.weight"].float()

def test_must_model_pt_is_state_dict_with_300d_embeddings():
    assert MODEL.exists()
    e = _emb(); assert e.ndim == 2 and e.shape[1] == 300, tuple(e.shape)

def test_must_vocab_pkl_structure():
    assert VOCAB.exists()
    v = _vocab(); assert isinstance(v.word_to_idx, dict) and isinstance(v.idx_to_word, list)

def test_must_vocab_at_least_3000_words():
    assert len(_vocab().word_to_idx) >= 3000

def test_must_vocab_mappings_consistent():
    v = _vocab(); assert len(v.word_to_idx) == len(v.idx_to_word)
    for w, i in v.word_to_idx.items(): assert v.idx_to_word[i] == w, w

def test_must_vocab_size_matches_embedding_rows():
    assert len(_vocab().word_to_idx) == _emb().shape[0]

def test_must_required_analogy_words_in_vocab():
    v = _vocab(); missing = [w for w in REQUIRED if w not in v.word_to_idx]; assert not missing, missing

def test_must_model_size_between_5_and_25MB():
    assert 5*1024*1024 <= MODEL.stat().st_size <= 25*1024*1024, MODEL.stat().st_size

def test_must_embeddings_meaningful_family_analogy():
    # mirrors official test_analogies: son-man+woman~daughter or father-man+woman~mother within top-75
    import numpy as np
    v = _vocab(); E = _emb().numpy(); E = E / np.linalg.norm(E, axis=1, keepdims=True)
    def ok(a, b, c, t):
        ids = [v.word_to_idx[x] for x in (a, b, c)]
        q = E[ids[0]] - E[ids[1]] + E[ids[2]]; q /= np.linalg.norm(q)
        order = np.argsort(-(E @ q)); ranked = [v.idx_to_word[i] for i in order if i not in ids and v.idx_to_word[i] != "unk"][:75]
        return t in ranked
    assert ok("son","man","woman","daughter") or ok("father","man","woman","mother")

def test_mustnot_wikitext_data_modified():
    assert TRAIN.exists() and VAL.exists()
    assert TRAIN.read_bytes().count(b"\n") == TRAIN_LINES and VAL.read_bytes().count(b"\n") == VAL_LINES

def test_mustnot_system_packages_uninstalled():
    # "A few python packages have been installed system-wide ... Please do not uninstall them."
    for m in ("torch", "numpy", "sklearn", "datasets", "pytest"):
        assert importlib.util.find_spec(m) is not None, m

def test_mustnot_embeddings_degenerate():
    # "learned" embeddings: not all-zero / not identical rows (a constant matrix would be hardcoded, not trained)
    if not MODEL.exists(): pytest.skip("no model yet")
    e = _emb(); assert e.abs().sum() > 0 and e.std(dim=0).mean() > 1e-4

def test_untested_pickled_class_named_exactly_Vocab_and_is_dataclass():
    # official tests substitute their own class for any pickle whose class is named 'Vocab' (and accept any
    # importable class with the right attrs); the instruction demands a dataclass named exactly `Vocab`
    _vocab(); assert _Rec.seen is not None and _Rec.seen[1] == "Vocab", _Rec.seen
    mod, name = _Rec.seen
    try:
        cls = getattr(importlib.import_module(mod), name)
    except Exception:
        pytest.skip(f"module {mod} not importable at test time; cannot verify dataclass-ness")
    assert dataclasses.is_dataclass(cls)
