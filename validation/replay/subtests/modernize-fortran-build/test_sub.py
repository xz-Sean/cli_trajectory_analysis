# E4 sub-tests for modernize-fortran-build. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import hashlib, os, re, shutil, subprocess, pytest
from pathlib import Path
from tempfile import TemporaryDirectory
APP = Path("/app"); MK = APP/"Makefile"; EXE = APP/"test_program"; OUT = APP/"output.txt"
SRC_MD5 = {"Makefile": "bf02d5d6597a2b21d433e8f53f44e8fd",
           "my_lib.f90": "97dfea493ba9613465613fbd2e40ed67",
           "test_main.f90": "e996a89cffb8e6e9ca45a4949d077c42"}
PAT = r"Calculated sum:\s*30\.00"

def _run_exe_in_tmp():
    """run the built binary in a scratch cwd so /app/output.txt is never touched"""
    with TemporaryDirectory() as d:
        r = subprocess.run([str(EXE)], cwd=d, capture_output=True, text=True, timeout=30)
        o = Path(d)/"output.txt"
        return r.returncode, (o.read_text() if o.exists() else None), r.stderr

def test_must_makefile_exists_in_app():
    assert MK.is_file() and MK.stat().st_size > 0

def test_must_makefile_invokes_gfortran():
    r = subprocess.run(["make", "-n", "-B"], cwd=str(APP), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr[-800:]
    assert "gfortran" in r.stdout and "ifort_proprietary_compiler" not in r.stdout, r.stdout[-800:]

def test_must_makefile_builds_from_clean():
    # build in a copy of /app so the final state is not modified
    with TemporaryDirectory() as d:
        for f in APP.iterdir():
            if f.is_file(): shutil.copy2(f, d)
        subprocess.run(["make", "clean"], cwd=d, capture_output=True, text=True, timeout=30)
        for f in ("test_program", "my_lib.o", "test_main.o"):
            Path(d, f).unlink(missing_ok=True)
        r = subprocess.run(["make"], cwd=d, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, (r.stdout + r.stderr)[-1200:]
        assert os.access(os.path.join(d, "test_program"), os.X_OK)

def test_must_test_program_built_and_executable():
    assert EXE.is_file() and os.access(str(EXE), os.X_OK)

def test_must_test_program_computes_30():
    rc, text, err = _run_exe_in_tmp()
    assert rc == 0 and text is not None, err[-500:]
    assert re.search(PAT, text), text

# DROPPED after calibration (oracle fails it):
#   test_must_output_txt_exists_in_app  -- the official test_makefile_compilation_process runs `make clean` (whose rule
#   deletes output.txt) before the sub-tests execute, so /app/output.txt never survives the official run even for the
#   oracle. Observation: the official tests themselves delete the file the instruction says "must not [be] modif[ied] or
#   delete[d]". The binary's output is checked instead by test_must_test_program_computes_30 (fresh run in a tmp cwd).

def test_mustnot_src_files_modified():
    for name, md5 in SRC_MD5.items():
        p = APP/"src"/name
        assert p.is_file(), f"{p} deleted"
        assert hashlib.md5(p.read_bytes()).hexdigest() == md5, f"{p} modified"

def test_mustnot_output_txt_tampered():
    if not OUT.is_file(): pytest.skip("no /app/output.txt in final state")
    rc, text, _ = _run_exe_in_tmp()
    assert rc == 0 and text is not None
    assert OUT.read_text() == text, "output.txt differs from what test_program writes"

def test_untested_makefile_text_no_proprietary_compiler():
    t = MK.read_text()
    assert "ifort_proprietary_compiler" not in t and "-fast" not in t.replace("# '-fast'", ""), t
