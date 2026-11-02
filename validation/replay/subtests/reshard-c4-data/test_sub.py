# E4 sub-tests for reshard-c4-data. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# The scripts are exercised on a small synthetic slice (60 jsonl files x 36 docs, c4-like text) under /tmp
# so the whole file runs in seconds; the official test covers the full-size unseen shard.
import hashlib, json, os, random, shutil, subprocess, uuid, pytest
from pathlib import Path
APP = Path("/app"); C4 = APP / "c4_sample"
COMPRESS, DECOMPRESS = APP / "compress.py", APP / "decompress.py"
MAX_ITEMS, MAX_BYTES = 30, 15 * 1024 * 1024
# shipped data (built by setup.py from c4 shard 00000): 9898 files, 817461269 bytes
C4_COUNT, C4_BYTES = 9898, 817461269
C4_MD5 = {"c4-mini-00000-of-10000.jsonl": "da75f3b32af7f5d97bb7b436ccceb31d",
          "c4-mini-04999-of-10000.jsonl": "bf9272d46e064953a8684d2d445922bf",
          "c4-mini-09897-of-10000.jsonl": "bad57fcf8f2bea39ea46d909b0da3857"}
_S = {}

def _walk(root, skip=(".venv", ".tbench-testing", "__pycache__", "c4_sample")):
    out = set()
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in skip]
        for f in fs: out.add(os.path.join(r, f))
    return out

def _state():
    """run compress then decompress once on a synthetic slice; cache everything the tests look at"""
    if _S: return _S
    if not (COMPRESS.exists() and DECOMPRESS.exists()):
        _S["err"] = "scripts missing"; return _S
    rng = random.Random(7); words = [f"w{i}" for i in range(3000)]
    base = Path(f"/tmp/e4_reshard_{uuid.uuid4().hex[:8]}"); inp, out = base / "in", base / "out"
    inp.mkdir(parents=True); orig = {}
    for i in range(60):
        lines = [json.dumps({"text": " ".join(rng.choice(words) for _ in range(rng.randint(150, 500))),
                             "url": f"http://example.com/{i}/{j}"}) for j in range(36)]
        p = inp / f"c4-mini-{i:05d}-of-10000.jsonl"; p.write_text("\n".join(lines) + "\n")
        orig[p.name] = p.read_bytes()
    before = {"app": _walk(APP), "tmp": set(os.listdir("/tmp")), "base": _walk(base)}
    r1 = subprocess.run(["uv", "run", str(COMPRESS), str(inp), str(out)], cwd="/app", capture_output=True, text=True, timeout=120)
    _S.update(orig=orig, base=base, inp=inp, out=out, rc1=r1.returncode, log1=(r1.stdout + r1.stderr)[-1500:])
    _S["out_exists"] = out.is_dir()
    _S["dirs"] = [(root, len(ds) + len(fs)) for root, ds, fs in os.walk(out)] if out.is_dir() else []
    _S["sizes"] = [(str(f), f.stat().st_size) for f in out.rglob("*") if f.is_file()] if out.is_dir() else []
    after = {"app": _walk(APP), "tmp": set(os.listdir("/tmp")), "base": _walk(base)}
    _S["outside"] = sorted((after["app"] - before["app"]) | {"/tmp/" + t for t in after["tmp"] - before["tmp"]}
                           | {p for p in after["base"] - before["base"] if not p.startswith(str(out))})
    shutil.rmtree(inp)   # like the official test: originals are gone before decompress
    r2 = subprocess.run(["uv", "run", str(DECOMPRESS), str(out)], cwd="/app", capture_output=True, text=True, timeout=120) if out.is_dir() else None
    _S["rc2"] = r2.returncode if r2 else None; _S["log2"] = (r2.stdout + r2.stderr)[-1500:] if r2 else ""
    _S["restored"] = {f.name: f.read_bytes() for f in out.iterdir()} if out.is_dir() else {}
    return _S

def _strip_hash(b): return hashlib.sha256(b.strip()).hexdigest()

def test_must_compress_script_exists():
    assert COMPRESS.is_file() and COMPRESS.stat().st_size > 0

def test_must_decompress_script_exists():
    assert DECOMPRESS.is_file() and DECOMPRESS.stat().st_size > 0

def test_must_compress_creates_output_dir_within_limits():
    s = _state(); assert "err" not in s, s["err"]
    assert s["rc1"] == 0, s["log1"]
    assert s["out_exists"], "output directory was not created"
    for d, n in s["dirs"]: assert n <= MAX_ITEMS, f"{d} has {n} entries > {MAX_ITEMS}"
    for f, n in s["sizes"]: assert n <= MAX_BYTES, f"{f} is {n} bytes > 15MB"

def test_must_decompress_restores_original_structure_and_content():
    s = _state(); assert "err" not in s, s["err"]
    assert s["rc2"] == 0, s["log2"]
    assert set(s["restored"]) == set(s["orig"]), "restored file set differs from original"
    for name, b in s["orig"].items():
        assert _strip_hash(s["restored"][name]) == _strip_hash(b), f"{name} content differs"

def test_mustnot_c4_sample_modified():
    files = [p for p in C4.iterdir() if p.is_file()]
    assert len(files) == C4_COUNT and sum(p.stat().st_size for p in files) == C4_BYTES, "c4_sample changed"
    for n, h in C4_MD5.items(): assert hashlib.md5((C4 / n).read_bytes()).hexdigest() == h, f"{n} modified"

def test_mustnot_compress_writes_outside_output_dir():
    s = _state()
    if "err" in s or s["rc1"] != 0: pytest.skip("compress did not run")
    assert s["outside"] == [], f"files created outside output dir: {s['outside'][:10]}"

# DROPPED after calibration (rule 1: oracle fails it):
#   test_untested_pyproject_and_uv_venv_in_app -- instruction: "must use a uv venv in /app and a pyproject.toml"; the
#   official test only prints a message when `uv sync` fails, and the reference solution.sh creates neither
#   /app/pyproject.toml nor /app/.venv (it relies on tqdm being present in the test venv). Observation for the paper:
#   the reference solution does not satisfy this stated requirement.

def test_untested_byte_exact_reconstruction():
    # instruction: "reconstruct the original file structure and content exactly" (official test compares stripped content)
    s = _state()
    if "err" in s or s["rc2"] != 0: pytest.skip("round trip did not run")
    for name, b in s["orig"].items(): assert s["restored"].get(name) == b, f"{name} not byte-identical"
