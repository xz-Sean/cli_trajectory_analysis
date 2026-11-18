# E4 sub-tests for fix-ocaml-gc. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# NOTE: the official run-tests.sh rebuilds the tree (make clean; ./configure; make -j4) and runs the basic testsuite
# into tests.txt before these sub-tests execute, so the in-tree binaries checked here are the ones built from the
# agent's final sources. Compile+run of the stress program takes < 2 s.
import hashlib, os, re, subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
OC = Path("/app/ocaml"); SH = OC/"runtime/shared_heap.c"; TESTS = OC/"tests.txt"
PRISTINE_MD5 = {"configure": "e0d2b0661e0d7c6d3f90db0ce32e3348", "Makefile": "aa129f9fecbcadf22f20ed7d166a68ae"}
GC_ML = r'''
let () =
  let keep = ref [] in
  for round = 1 to 30 do
    let l = ref [] in
    for i = 1 to 20000 do
      let n = 1 + (i * 7 + round) mod 40 in
      l := Array.make n i :: !l;
      if i mod 3 = 0 then keep := Array.make (1 + (i mod 11)) i :: !keep
    done;
    Gc.full_major ();
    if List.length !keep > 50000 then keep := [];
    ignore (List.length !l)
  done;
  Gc.full_major (); Gc.compact ();
  print_string "GC_OK"
'''

def _stress(native):
    with TemporaryDirectory() as d:
        src = Path(d)/"gc.ml"; src.write_text(GC_ML); exe = f"{d}/gc.exe"
        comp = [str(OC/"ocamlopt.opt")] if native else [str(OC/"runtime/ocamlrun"), str(OC/"ocamlc")]
        r = subprocess.run(comp + ["-nostdlib", "-I", str(OC/"stdlib"), str(src), "-o", exe],
                           capture_output=True, text=True, timeout=40, cwd=d)
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
        run = [exe] if native else [str(OC/"runtime/ocamlrun"), exe]
        r = subprocess.run(run, capture_output=True, text=True, timeout=40, cwd=d)
        assert r.returncode == 0 and r.stdout.strip() == "GC_OK", (r.returncode, r.stdout[-200:], r.stderr[-500:])

def test_must_shared_heap_source_present():
    assert SH.is_file() and SH.stat().st_size > 0

def test_must_compiler_bootstraps():
    # bootstrapping crashed in the broken tree, so ocamlc is never produced there
    for f in ("runtime/ocamlrun", "ocamlc", "ocamlopt.opt"):
        assert os.access(OC/f, os.X_OK), f"{f} not built"

def test_must_basic_testsuite_runs_cleanly():
    assert TESTS.is_file(), "tests.txt missing"
    t = TESTS.read_text()
    assert re.search(r"^\s*40 tests passed", t, re.M), t[-600:]
    assert re.search(r"^\s*0 tests failed", t, re.M) and re.search(r"^\s*0 unexpected errors", t, re.M), t[-600:]

def test_must_bytecode_runtime_survives_major_gc_sweep():
    _stress(native=False)

def test_mustnot_run_length_sweeping_change_reverted():
    # the task is to fix the new run-length-compressed free blocks, not to remove the feature
    t = SH.read_text()
    assert "POOL_FREE_HEADER" in t and "POOL_BLOCK_FREE_HD" in t, "run-length free-block machinery removed"

def test_mustnot_build_system_tampered():
    for f, md5 in PRISTINE_MD5.items():
        assert hashlib.md5((OC/f).read_bytes()).hexdigest() == md5, f"{f} modified"

def test_untested_native_runtime_survives_major_gc_sweep():
    _stress(native=True)
