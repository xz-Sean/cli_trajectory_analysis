# E4 sub-tests for neuron-to-jaxley-conversion. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# NOTE: RGC() (loading RGC.swc) takes ~50 s, so the behavioural tests inject a small 6-branch
# cell carrying the same six groups (soma/dend/AH/SOCB/NR/axon) into an RGC instance and compare
# the agent's add_channels() against the reference add_channels_solution() from /tests/functions.py.
import hashlib, re, sys, os, pytest
from pathlib import Path
APP = Path("/app"); SRC = APP / "jaxley_conversion.py"
ORIG_MD5 = {"RGC.swc": "f69168828d45dd0124b560b74357e348", "sec_lu.pkl": "fcb54cf92c3fbe3d15a4b4a662a976b2",
            "build_in_neuron.py": "df40cc105405920779fd0c89c5e43a9c", "generating_from_swc.py": "3e9ff21525d1d4f01fde9a9f3b2a824f",
            "axon_ellipse.py": "7af28cbb5dbe38cbf15947bbeb88baa5"}
_CACHE = {}

def _rgc_cls():
    sys.path.insert(0, "/app")
    import jaxley_conversion
    return jaxley_conversion.RGC

def _small_cell():
    import jaxley as jx
    cell = jx.Cell(jx.Branch(jx.Compartment(), ncomp=2), parents=[-1, 0, 0, 1, 1, 2])
    for i, g in enumerate(["soma", "dend", "AH", "SOCB", "NR", "axon"]):
        cell.branch(i).add_to_group(g)
    cell.compute_compartment_centers(); cell.initialize()
    return cell

def _agent_cell():
    if "agent" not in _CACHE:
        RGC = _rgc_cls(); obj = RGC.__new__(RGC); obj.cell = _small_cell()
        obj.add_channels(); _CACHE["agent"] = obj
    return _CACHE["agent"]

def _traces():
    """(agent, reference) spike traces of shape (4, ncomp, T): v, i_HH, i_Ca, i_KCa"""
    if "traces" not in _CACHE:
        if not Path("/tests/functions.py").exists(): pytest.skip("reference /tests/functions.py not available")
        sys.path.insert(0, "/tests")
        from functions import add_channels_solution, spike
        a = spike(_agent_cell().get_cell()); b = spike(add_channels_solution(_small_cell()))
        _CACHE["traces"] = (a, b)
    return _CACHE["traces"]

def test_must_add_channels_defined_in_RGC():
    assert SRC.exists()
    RGC = _rgc_cls()
    assert callable(getattr(RGC, "add_channels", None)), "RGC.add_channels missing"

def test_must_add_channels_inserts_channels():
    cell = _agent_cell().get_cell()
    assert len(cell.channels) > 0, "no channels inserted into the cell"

def test_must_voltage_matches_neuron_reference():
    import numpy as np
    a, b = _traces()
    assert a.shape == b.shape and np.allclose(a[0], b[0]), "membrane voltage trace differs from reference"

def test_must_currents_match_neuron_reference():
    import numpy as np
    a, b = _traces()
    for k, name in ((1, "i_HH"), (2, "i_Ca"), (3, "i_KCa")):
        assert np.allclose(a[k], b[k]), f"{name} trace differs from reference"

def test_mustnot_input_files_modified():
    for f, h in ORIG_MD5.items():
        p = APP / f
        assert p.exists(), f"{f} deleted"
        assert hashlib.md5(p.read_bytes()).hexdigest() == h, f"{f} modified"

def test_mustnot_rgc_interface_changed():
    # template interface must survive: RGC() still builds the cell from RGC.swc and get_cell() returns it
    src = SRC.read_text()
    assert re.search(r"generate_cell\(\s*['\"]RGC\.swc['\"]", src), "RGC no longer loads RGC.swc via generate_cell"
    if not callable(getattr(_rgc_cls(), "add_channels", None)): pytest.skip("add_channels not implemented yet")
    obj = _agent_cell()
    assert obj.get_cell() is obj.cell

# UNTESTED: none — the instruction's only requirements (add_channels in RGC, biophysics added to the loaded cell)
# are covered by the official spike-equivalence test.
