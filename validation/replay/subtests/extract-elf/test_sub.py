# E4 sub-tests for extract-elf. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# The official test only exercises a freshly compiled /app/new.o; the instruction names /app/a.out.
import json, hashlib, struct, subprocess, tempfile, os, pytest
from pathlib import Path
JS = Path("/app/extract.js"); AOUT = Path("/app/a.out"); HIC = Path("/app/hi.c")
HIC_MD5 = "b9c977a7420567de78bbd6edc3edcea8"   # task-deps/hi.c as COPY'd
AOUT_MD5 = "6235f9045c8f118f416d37eee4fff056"                       # a.out as compiled in the pristine image (filled in during calibration)

def _reference(path):
    """python port of the reference extractor: 4-byte LE words of .text/.data/.rodata keyed by decimal vaddr"""
    b = Path(path).read_bytes(); assert b[:4] == b"\x7fELF"
    cls, le = b[4], b[5] == 1
    assert le, "reference only handles little-endian"
    if cls == 2:
        shoff = struct.unpack_from("<Q", b, 0x28)[0]; shentsize, shnum, shstrndx = struct.unpack_from("<HHH", b, 0x3A)
    else:
        shoff = struct.unpack_from("<I", b, 0x20)[0]; shentsize, shnum, shstrndx = struct.unpack_from("<HHH", b, 0x2E)
    secs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        if cls == 2:
            name, typ, flags, addr, off, size = struct.unpack_from("<IIQQQQ", b, o)
        else:
            name, typ, flags, addr, off, size = struct.unpack_from("<IIIIII", b, o)
        secs.append((name, addr, off, size))
    sn, sa, so, ss = secs[shstrndx]; strtab = b[so:so + ss]
    mem = {}
    for name, addr, off, size in secs:
        end = strtab.index(b"\0", name); nm = strtab[name:end].decode()
        if nm in (".text", ".data", ".rodata"):
            data = b[off:off + size]
            for i in range(0, len(data) - 3, 4):
                mem[str(addr + i)] = struct.unpack_from("<I", data, i)[0]
    return mem

def _run(binary):
    r = subprocess.run(["node", str(JS), str(binary)], capture_output=True, text=True, cwd="/app", timeout=60)
    return r

def _check(out, ref):
    bad = {k: (v, ref[k]) for k, v in out.items() if k in ref and ref[k] != v}
    assert not bad, f"{len(bad)} addresses with wrong values, e.g. {list(bad.items())[:3]}"
    cov = sum(1 for k in ref if k in out) / len(ref)
    assert cov >= 0.75, f"only {cov:.1%} of reference addresses present"

def test_must_extract_js_exists():
    assert JS.is_file() and JS.stat().st_size > 0

def test_must_runs_on_a_out_and_prints_json_object():
    r = _run(AOUT); assert r.returncode == 0, r.stderr[-800:]
    d = json.loads(r.stdout); assert isinstance(d, dict) and len(d) > 0

def test_must_keys_are_addresses_and_values_are_integers():
    d = json.loads(_run(AOUT).stdout)
    for k, v in d.items():
        assert k.isdigit(), k
        assert type(v) is int, (k, v)

def test_must_values_match_reference_and_cover_75pct_on_a_out():
    _check(json.loads(_run(AOUT).stdout), _reference(AOUT))

def test_must_generalises_to_a_fresh_binary():
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "e4.c"; exe = Path(d) / "e4.bin"
        src.write_text('#include<stdio.h>\nint main(int c,char**v){for(int i=0;i<c;i++)printf("E4 %d %s\\n",i,v[i]);return c*7;}\n')
        assert subprocess.run(["gcc", "-o", str(exe), str(src)], capture_output=True).returncode == 0
        r = _run(exe); assert r.returncode == 0, r.stderr[-500:]
        _check(json.loads(r.stdout), _reference(exe))

def test_mustnot_a_out_modified():
    assert AOUT.exists() and hashlib.md5(AOUT.read_bytes()).hexdigest() == AOUT_MD5

def test_mustnot_hi_c_modified():
    assert HIC.exists() and hashlib.md5(HIC.read_bytes()).hexdigest() == HIC_MD5

def test_mustnot_output_hardcoded():
    if not JS.exists(): pytest.skip("no extract.js yet")
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "e4b.c"; exe = Path(d) / "e4b.bin"
        src.write_text('int main(){volatile int x=0x5eed;return x;}\n')
        assert subprocess.run(["gcc", "-o", str(exe), str(src)], capture_output=True).returncode == 0
        a = _run(AOUT).stdout.strip(); b = _run(exe).stdout.strip()
        assert a != b, "same output for two different binaries"

def test_untested_stdout_is_pure_json():
    # "node extract.js /app/a.out > out.json": stdout must be nothing but the JSON document
    r = _run(AOUT); assert r.returncode == 0
    json.loads(r.stdout)          # raises if anything besides the object is printed
    assert r.stdout.strip().startswith("{") and r.stdout.strip().endswith("}")
