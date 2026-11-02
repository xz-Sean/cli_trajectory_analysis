# E4 sub-tests for triton-interpret. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import os, re, sys, hashlib, inspect, subprocess, importlib.util, pytest
from pathlib import Path
os.environ["TRITON_INTERPRET"] = "1"
SOL = Path("/app/triton_agent_sol.py"); REF = Path("/app/torch_implementation.py")
REF_MD5 = "69781a75ee42c72b1cbadbf2246bfd65"   # md5 of tests/torch_implementation.py as COPY'd by the Dockerfile

def _load():
    sys.path.insert(0, "/app")
    spec = importlib.util.spec_from_file_location("triton_agent_sol_e4", str(SOL))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _ref(D, width, eps=1e-6):
    import torch
    sys.path.insert(0, "/app")
    from torch_implementation import Gated
    return Gated(D, width=width, eps=eps).eval()

def test_must_solution_file_exists():
    assert SOL.exists() and SOL.stat().st_size > 0

def test_must_defines_gate_triton_with_triton_jit_kernel():
    assert "@triton.jit" in SOL.read_text()
    m = _load(); assert callable(getattr(m, "gate_triton", None))

def test_must_equivalent_to_pytorch_on_unseen_shape():
    import torch
    m = _load(); torch.manual_seed(7)
    B, S, D, width = 2, 5, 8, 3
    mod = _ref(D, width); x = torch.randn(B, S, D, dtype=torch.float32)
    with torch.no_grad(): y_ref = mod(x)
    y = m.gate_triton(x, mod.weight, mod.alpha, mod.rmsnorm.weight, eps=1e-6)
    assert y.shape == y_ref.shape and torch.allclose(y_ref, y, atol=1e-4, rtol=1e-4), (y_ref - y).abs().max()

def test_must_no_tl_sum_in_code_or_comments():
    src = SOL.read_text()
    assert "tl.sum" not in src and "triton.language.sum" not in src

def test_mustnot_reference_implementation_modified():
    assert REF.exists() and hashlib.md5(REF.read_bytes()).hexdigest() == REF_MD5

def test_mustnot_torch_or_numpy_calls_inside_kernels():
    # static check: no torch./np./numpy. attribute access inside any @triton.jit-decorated function body
    if not SOL.exists(): pytest.skip("no solution yet")
    src = SOL.read_text().splitlines(); bad = []
    i = 0
    while i < len(src):
        if src[i].strip().startswith("@triton.jit"):
            j = i + 1
            while j < len(src) and not src[j].strip().startswith("def "): j += 1
            indent = len(src[j]) - len(src[j].lstrip()); j += 1
            while j < len(src) and (not src[j].strip() or len(src[j]) - len(src[j].lstrip()) > indent):
                code = src[j].split("#", 1)[0]
                if re.search(r"\b(torch|np|numpy)\.", code): bad.append(src[j].strip())
                j += 1
            i = j
        else: i += 1
    assert not bad, bad

def test_untested_sets_TRITON_INTERPRET_in_solution_file():
    assert re.search(r"TRITON_INTERPRET[\"']?\s*\]?\s*=\s*[\"']1[\"']", SOL.read_text()), "solution must set TRITON_INTERPRET=1 itself"

def test_untested_signature_matches_spec():
    m = _load(); p = inspect.signature(m.gate_triton).parameters
    assert list(p) == ["x", "weight", "alpha", "rms_weight", "eps"] and p["eps"].default == 1e-6, list(p)

def test_untested_alpha_none_width_1():
    import torch
    m = _load(); torch.manual_seed(1)
    mod = _ref(8, 1); x = torch.randn(2, 4, 8, dtype=torch.float32)
    assert mod.alpha is None
    with torch.no_grad(): y_ref = mod(x)
    y = m.gate_triton(x, mod.weight, None, mod.rmsnorm.weight, eps=1e-6)
    assert torch.allclose(y_ref, y, atol=1e-4, rtol=1e-4)

def test_untested_output_dtype_matches_input():
    import torch
    m = _load(); torch.manual_seed(2)
    mod = _ref(8, 2); x = torch.randn(1, 3, 8).to(torch.float64)
    y = m.gate_triton(x, mod.weight, mod.alpha, mod.rmsnorm.weight)
    assert y.dtype == x.dtype and y.shape == x.shape

def test_untested_triton_340_installed_in_system_python():
    # instruction step 1: install Triton 3.4.0 (the official tests bring their own venv, so this is never checked)
    r = subprocess.run(["/usr/local/bin/python3", "-c", "import triton, torch; print(triton.__version__)"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "3.4.0", r.stdout + r.stderr[-500:]
