# E4 sub-tests for flood-monitoring-basic. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import csv, json, pytest
from pathlib import Path
DATA = Path("/data"); SUMMARY = Path("/app/flood_summary.json")
STATIONS = ["station_A", "station_B", "station_C"]
# original (pre-fill) data from the Dockerfile: None = empty cell
ORIG = {
 "station_A": [None,2.3,2.5,2.8,3.2,None,3.7,3.9,4.2,4.5,4.3,3.8,3.4,3.0,2.8,2.6,2.4,2.5,2.7,2.9,None,3.4,3.6,3.8,
               4.0,4.1,3.9,3.7,3.5,3.3,3.1,2.9,2.7,2.5,2.3,2.1,None,2.0,2.1,2.2,2.3,2.4,2.5,2.4,2.3,2.2,2.1,None],
 "station_B": [1.8,2.0,2.2,2.4,2.6,2.8,3.0,3.2,3.4,None,3.8,4.0,4.2,4.1,3.9,3.7,3.5,3.3,3.1,2.9,2.7,2.5,2.3,2.1,
               2.0,2.1,2.2,2.3,2.4,2.5,None,2.7,2.8,2.9,3.0,2.9,2.8,2.7,2.6,2.5,2.4,2.3,2.2,2.1,2.0,1.9,1.8,1.7],
 "station_C": [1.5,1.6,1.7,1.8,1.9,2.0,2.1,2.2,2.3,2.4,2.5,2.6,2.7,2.8,2.9,3.0,3.1,3.2,3.3,3.4,3.3,3.2,3.1,3.0,
               2.9,2.8,2.7,2.6,2.5,2.4,2.3,2.2,2.1,2.0,1.9,1.8,1.7,1.6,1.5,1.4,1.3,1.4,1.5,1.6,1.7,1.8,1.7,1.6]}
EXPECTED_FILL = {"station_A": {0: 2.3, 5: 3.45, 20: 3.15, 36: 2.05, 47: 2.1}, "station_B": {9: 3.6, 30: 2.6}}
EXPECTED_COUNTS = {"station_A": 2, "station_B": 1, "station_C": 0}

def _rows(st):
    with open(DATA/f"{st}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def test_must_csvs_overwritten_in_place_48_rows_no_missing():
    for st in STATIONS:
        rows = _rows(st); assert len(rows) == 48, (st, len(rows))
        for i, r in enumerate(rows):
            assert r["water_level_m"] not in ("", None), (st, i); float(r["water_level_m"])

def test_must_start_end_filled_with_nearest_available():
    v = [float(r["water_level_m"]) for r in _rows("station_A")]
    assert abs(v[0] - 2.3) < 1e-6 and abs(v[47] - 2.1) < 1e-6, (v[0], v[47])

def test_must_middle_values_linearly_interpolated():
    for st, exp in EXPECTED_FILL.items():
        v = [float(r["water_level_m"]) for r in _rows(st)]
        for i, e in exp.items():
            if st == "station_A" and i in (0, 47): continue
            assert abs(v[i] - e) < 1e-6, (st, i, v[i], e)

def test_must_summary_json_exists_with_int_counts():
    assert SUMMARY.is_file(); d = json.loads(SUMMARY.read_text())
    assert isinstance(d, dict)
    for st in STATIONS: assert st in d and type(d[st]) is int, d

def test_must_flood_event_counts_correct():
    d = json.loads(SUMMARY.read_text())
    for st, n in EXPECTED_COUNTS.items(): assert d[st] == n, (st, d[st])

def test_mustnot_existing_readings_or_timestamps_altered():
    for st in STATIONS:
        rows = _rows(st)
        if len(rows) != 48 or any(r["water_level_m"] == "" for r in rows): pytest.skip("csv not completed yet")
        for i, (r, o) in enumerate(zip(rows, ORIG[st])):
            assert r["timestamp"] == f"2024-01-{1 + i//24:02d} {i%24:02d}:00", (st, i, r["timestamp"])
            if o is not None: assert abs(float(r["water_level_m"]) - o) < 1e-9, (st, i, r["water_level_m"], o)

def test_untested_csv_header_preserved():
    for st in STATIONS:
        first = (DATA/f"{st}.csv").read_text(encoding="utf-8").splitlines()[0].strip()
        assert first == "timestamp,water_level_m", (st, first)

def test_untested_summary_has_exactly_three_station_keys():
    d = json.loads(SUMMARY.read_text()); assert set(d.keys()) == set(STATIONS), d.keys()
