# neuron-to-jaxley-conversion — sub-test calibration

Build: ok (`e4/neuron-to-jaxley-conversion`, pip installs jaxley 0.10.0 / jax 0.6.2). Oracle: solution.sh present (appends
add_channels + channel classes to /app/jaxley_conversion.py).

Design note: `RGC()` (generate_cell on RGC.swc, 959 branches with per-branch set_ncomp) takes ~50 s, and the official test
builds two of them, so the behavioural sub-tests inject a small 6-branch cell carrying the same six groups
(soma/dend/AH/SOCB/NR/axon) into an `RGC` instance (`RGC.__new__`) and compare the agent's `add_channels()` against the reference
`add_channels_solution()` from /tests/functions.py with the official `spike()` protocol. Whole file runs in ~8–12 s. On the
oracle the small-cell traces are bit-identical to the reference (max abs diff 0.0).

| sub-test | group | status | reason |
|---|---|---|---|
| test_must_add_channels_defined_in_RGC | must | kept | RGC.add_channels exists and is callable |
| test_must_add_channels_inserts_channels | must | kept | after add_channels() the cell has >= 1 channel |
| test_must_voltage_matches_neuron_reference | must | kept | membrane voltage trace allclose to the reference (official semantics, per quantity) |
| test_must_currents_match_neuron_reference | must | kept | i_HH, i_Ca, i_KCa traces allclose to the reference |
| test_mustnot_input_files_modified | mustnot | kept | md5 of RGC.swc, sec_lu.pkl, build_in_neuron.py, generating_from_swc.py, axon_ellipse.py |
| test_mustnot_rgc_interface_changed | mustnot | rewritten (skips functional part while add_channels is absent) | RGC still loads RGC.swc via generate_cell and get_cell() returns self.cell |
| (untested) | — | none | the instruction's requirements are fully covered by the official spike-equivalence test |

Calibration (e4_calibrate.py, final run):
```
[neuron-to-jaxley-conversion] pristine: official 0/1 | must 0/4 mustnot 1/1 untested 0/0 | oracle_rc=None
[neuron-to-jaxley-conversion] oracle  : official 1/1 | must 4/4 mustnot 2/2 untested 0/0 | oracle_rc=0
```
First run (before making the mustnot skip on the pristine image): pristine `must 0/4 mustnot 1/2`, oracle `must 4/4 mustnot 2/2`.
Rule 1 ok, rule 3 ok (4 must fail on pristine). Dropped: 0.

Irreversibility potential: high — the oracle appends to /app/jaxley_conversion.py with `cat >>`; if the agent rewrote the
template (e.g. removed the RGC class/get_cell, changed generate_cell) or deleted RGC.swc/sec_lu.pkl, the oracle can no longer
produce a passing state. A half-written add_channels left in the file also makes the oracle's appended method shadow/duplicate it.
