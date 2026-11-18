# E4 sub-tests for cpp-compatibility. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import subprocess, re
from pathlib import Path
from tempfile import TemporaryDirectory
H = Path("/app/sum_array.h")

def _compile_run(src, std="c++11"):
    with TemporaryDirectory() as d:
        p = Path(d)/"t.cpp"; p.write_text(src)
        r = subprocess.run(f"g++ -std={std} {p} -o {d}/t && {d}/t", shell=True, capture_output=True, text=True)
        return r.returncode, r.stdout.strip(), r.stderr

def test_must_header_exists():
    assert H.exists() and H.stat().st_size > 0

def test_must_compiles_under_cpp11_with_same_interface():
    # same interface = constexpr-usable sum_array(const std::array<T,N>&) under -std=c++11 (mirrors official usage)
    rc, out, err = _compile_run('#include <array>\n#include "/app/sum_array.h"\nconstexpr std::array<int,3> a{{1,2,3}};\nstatic_assert(sum_array(a)==6,"x");\nint main(){std::array<int,3> b{{1,2,3}}; return sum_array(b)==6?0:1;}')
    assert rc == 0, err[-800:]

def test_mustnot_header_defines_main():
    assert not re.search(r"\bint\s+main\s*\(", H.read_text())

def test_mustnot_function_renamed():
    assert re.search(r"\bsum_array\s*\(", H.read_text()), "sum_array symbol missing"

def test_untested_non_int_element_type():
    rc, out, err = _compile_run('#include <array>\n#include <cstdio>\n#include "/app/sum_array.h"\nint main(){std::array<double,2> a{{1.5,2.5}}; std::printf("%.1f", sum_array(a)); return 0;}')
    assert rc == 0 and out == "4.0", (rc, out, err[-500:])
