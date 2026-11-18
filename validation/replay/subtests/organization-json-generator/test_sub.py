# E4 sub-tests for organization-json-generator. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import csv, hashlib, json, subprocess, pytest
from collections import Counter
from pathlib import Path
APP = Path("/app"); OUT = APP / "organization.json"; DATA = APP / "data"
ORIG_MD5 = {"data/departments.csv": "2c9a617ad11eebba46b88f659ceddfa4", "data/employees.csv": "497b0efff94f033da396cdb9feb23c3a",
            "data/projects.csv": "184ee8d8ca5639d99cf041f4128bec78", "schema.json": "083ed105a21a4bde529bb3bf486dfe15"}
STATUSES = {"Planning", "In Progress", "Testing", "Completed", "On Hold"}

def _doc():
    if not OUT.exists(): pytest.fail("/app/organization.json missing")
    return json.loads(OUT.read_text())

def _csv(name):
    with (DATA / name).open() as f: return list(csv.DictReader(f))

def test_must_output_exists_and_is_json_object():
    assert isinstance(_doc(), dict)

def test_must_follows_schema_required_keys_and_types():
    d = _doc()
    assert {"metadata", "organization", "statistics"} <= set(d)
    m = d["metadata"]; assert all(isinstance(m.get(k), str) for k in ("version", "timestamp", "generator")), m
    o = d["organization"]; assert isinstance(o.get("name"), str) and isinstance(o.get("founded"), str)
    assert isinstance(o.get("departments"), list) and len(o["departments"]) >= 3
    for dep in o["departments"]:
        assert isinstance(dep["id"], str) and isinstance(dep["name"], str) and isinstance(dep["budget"], (int, float)) and dep["budget"] >= 0
        assert isinstance(dep["employees"], list) and len(dep["employees"]) >= 2 and isinstance(dep["projects"], list)
        for e in dep["employees"]:
            assert all(isinstance(e[k], str) for k in ("id", "name", "position")), e
            assert isinstance(e["skills"], list) and e["skills"] and all(isinstance(s, str) for s in e["skills"])
            assert isinstance(e["years_of_service"], int) and not isinstance(e["years_of_service"], bool) and e["years_of_service"] >= 0
        for p in dep["projects"]:
            assert isinstance(p["name"], str) and p["status"] in STATUSES and isinstance(p["deadline"], str)
            assert isinstance(p["members"], list) and all(isinstance(x, str) for x in p["members"])
    s = d["statistics"]
    for k in ("averageDepartmentBudget", "totalEmployees", "skillDistribution", "departmentSizes", "projectStatusDistribution", "averageYearsOfService"):
        assert k in s, f"statistics.{k} missing"
    for k in ("skillDistribution", "departmentSizes", "projectStatusDistribution"):
        assert isinstance(s[k], dict) and all(isinstance(v, int) for v in s[k].values()), k

def test_must_departments_and_employees_from_csv():
    deps = {d["id"]: d for d in _doc()["organization"]["departments"]}
    assert set(deps) == {r["id"] for r in _csv("departments.csv")}
    for r in _csv("departments.csv"):
        assert deps[r["id"]]["name"] == r["name"] and float(deps[r["id"]]["budget"]) == float(r["budget"]), r
    emp_by_dep = {}
    for r in _csv("employees.csv"): emp_by_dep.setdefault(r["department_id"], {})[r["id"]] = r
    for did, dep in deps.items():
        got = {e["id"]: e for e in dep["employees"]}
        assert set(got) == set(emp_by_dep.get(did, {})), f"employees of {did} differ from CSV"
        for eid, r in emp_by_dep[did].items():
            e = got[eid]
            assert e["name"] == r["name"] and e["position"] == r["position"], e
            assert e["skills"] == r["skills"].split(";") and e["years_of_service"] == int(r["years_of_service"]), e

def test_must_projects_from_csv():
    deps = {d["id"]: d for d in _doc()["organization"]["departments"]}
    want = {}
    for r in _csv("projects.csv"): want.setdefault(r["department_id"], {})[r["name"]] = r
    for did, dep in deps.items():
        got = {p["name"]: p for p in dep["projects"]}
        assert set(got) == set(want.get(did, {})), f"projects of {did} differ from CSV"
        for name, r in want.get(did, {}).items():
            p = got[name]
            assert p["status"] == r["status"] and p["deadline"] == r["deadline"], p
            assert sorted(p["members"]) == sorted(r["member_ids"].split(";")), p

def test_must_statistics_values():
    s = _doc()["statistics"]
    assert abs(s["averageDepartmentBudget"] - 1060000.0) < 0.01, s["averageDepartmentBudget"]
    assert s["totalEmployees"] == 12
    assert s["departmentSizes"] == {"Engineering": 3, "Marketing": 2, "Human Resources": 2, "Research & Development": 3, "Customer Support": 2}
    assert s["projectStatusDistribution"] == {"In Progress": 3, "Completed": 1, "Planning": 1, "Testing": 1, "On Hold": 1}

def test_mustnot_input_data_or_schema_modified():
    for f, h in ORIG_MD5.items():
        assert (APP / f).exists(), f"{f} deleted"
        assert hashlib.md5((APP / f).read_bytes()).hexdigest() == h, f"{f} modified"

def test_untested_skill_distribution_and_average_years():
    # schema-required statistics the official tests never check
    s = _doc()["statistics"]
    skills = Counter(sk for r in _csv("employees.csv") for sk in r["skills"].split(";"))
    assert s["skillDistribution"] == dict(skills), s["skillDistribution"]
    assert abs(s["averageYearsOfService"] - 7.25) < 0.01, s["averageYearsOfService"]

def test_untested_validates_against_schema_json():
    # instruction: "following the schema defined in /app/schema.json" -- run the real validator (jsonschema is in the image's system python)
    if not OUT.exists(): pytest.fail("/app/organization.json missing")
    code = "import json,jsonschema,sys; jsonschema.validate(json.load(open('/app/organization.json')), json.load(open('/app/schema.json')))"
    r = subprocess.run(["/usr/local/bin/python", "-c", code], capture_output=True, text=True)
    if "ModuleNotFoundError" in r.stderr: pytest.skip("jsonschema not importable in system python")
    assert r.returncode == 0, r.stderr[-800:]

def test_untested_generator_script_exists():
    # instruction: "Create a JSON processor that transforms CSV data" -- official tests only inspect the output file
    cand = [p for p in APP.rglob("*") if p.suffix in (".py", ".sh", ".js") and ".tbench-testing" not in p.parts and "tests" not in p.parts]
    assert any("organization.json" in p.read_text(errors="ignore") for p in cand), "no processor script in /app refers to organization.json"
