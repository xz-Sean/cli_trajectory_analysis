# E4 sub-tests for intrusion-detection. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import hashlib, json, os, re, subprocess, time, pytest
from pathlib import Path
from datetime import datetime, timezone
APP = Path("/app"); DET = APP / "intrusion_detector.sh"; RESP = APP / "response.sh"
ORIG_MD5 = {"logs/auth.log": "b523c065d90eb4beb44b3e9aca8b5abe", "logs/http.log": "9a41747d3ef459be52463343bd22b6f4",
            "rules/detection_rules.json": "63f5bb886cfd1b3e5ac4b77256ac24d4"}
RULES = {"SSH-BRUTE-FORCE": ("high", 5), "WEB-SCAN": ("medium", 3), "INVALID-USER": ("low", 2), "SUDO-COMMAND": ("info", 1)}
# rules that fire on the shipped logs under any reading of the thresholds, and an IP each must list
EXPECTED = {"SSH-BRUTE-FORCE": "45.32.67.89", "WEB-SCAN": "45.32.67.89", "INVALID-USER": "198.51.100.23", "SUDO-COMMAND": None}
BAD_IP = "45.32.67.89"; ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_S = {}

def _run_detector():
    if "det" not in _S:
        if not DET.exists(): pytest.fail("/app/intrusion_detector.sh missing")
        r = subprocess.run([str(DET)], cwd="/app", capture_output=True, text=True, timeout=30)
        _S["det"] = r; _S["det_t"] = time.time()
    r = _S["det"]; assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return json.loads((APP / "alert.json").read_text()), json.loads((APP / "report.json").read_text())

def _run_response():
    if "resp" not in _S:
        if not RESP.exists(): pytest.fail("/app/response.sh missing")
        before = set(os.listdir("/app"))
        r = subprocess.run([str(RESP), BAD_IP], cwd="/app", capture_output=True, text=True, timeout=30)
        new = [f for f in set(os.listdir("/app")) - before if "incident" in f and BAD_IP in f]
        _S["resp"] = (r, new)
    r, new = _S["resp"]; assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert new, "no incident_<IP>_<timestamp>.txt report was created in /app"
    return new, (APP / new[0]).read_text()

def test_must_scripts_exist_and_executable():
    for s in (DET, RESP): assert s.exists() and os.access(s, os.X_OK), s

def test_must_alert_json_schema_and_content():
    alert, _ = _run_detector()
    assert ISO.match(str(alert.get("timestamp", ""))), alert.get("timestamp")
    byid = {a["id"]: a for a in alert["alerts"]}
    assert set(byid) <= set(RULES), f"unknown rule ids {set(byid) - set(RULES)}"
    for rid, ip in EXPECTED.items():
        assert rid in byid, f"{rid} should have fired on the shipped logs"
        a = byid[rid]; sev, thr = RULES[rid]
        assert a["severity"] == sev and isinstance(a["matches"], int) and a["matches"] >= thr, a
        assert isinstance(a["ips"], str) and (ip is None or ip in a["ips"].split(",")), a

def test_must_report_json_schema_and_content():
    alert, rep = _run_detector()
    assert ISO.match(str(rep.get("timestamp", ""))), rep.get("timestamp")
    assert isinstance(rep["events"], list) and isinstance(rep["statistics"], dict)
    assert {e["id"] for e in rep["events"]} == {a["id"] for a in alert["alerts"]}, "events must mirror alerts"
    for rid, (sev, thr) in RULES.items():
        if rid in EXPECTED:
            assert isinstance(rep["statistics"].get(rid), int) and rep["statistics"][rid] >= thr, rep["statistics"]

def test_must_response_creates_incident_report_with_activity():
    _, txt = _run_response()
    assert BAD_IP in txt
    assert re.search(r"Failed password", txt) and re.search(r"GET /(admin|phpmyadmin|wp-admin)", txt), "suspicious activity not summarised"

def test_must_invalid_ip_nonzero_exit():
    if not RESP.exists(): pytest.fail("/app/response.sh missing")
    for bad in ("999.999.999.999", "not-an-ip"):
        r = subprocess.run([str(RESP), bad], cwd="/app", capture_output=True, text=True, timeout=30)
        assert r.returncode != 0, f"exit 0 for invalid ip {bad}"

def test_mustnot_logs_or_rules_modified():
    for f, h in ORIG_MD5.items():
        p = APP / f; assert p.exists(), f"{f} deleted"
        assert hashlib.md5(p.read_bytes()).hexdigest() == h, f"{f} modified"

def test_mustnot_alert_timestamp_hardcoded():
    if not DET.exists(): pytest.skip("no detector yet")
    alert, _ = _run_detector()
    ts = str(alert["timestamp"]).replace("Z", "+00:00")
    try: t = datetime.fromisoformat(ts)
    except ValueError: pytest.fail(f"timestamp not ISO-8601: {ts}")
    if t.tzinfo is None: t = t.replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - t).total_seconds()) < 86400, f"timestamp {ts} is not the generation time"

def test_untested_invalid_ip_echoes_invalid():
    # instruction: "...raise an error exit-code AND echo the word 'invalid'"; the official test only checks the message when rc==0
    if not RESP.exists(): pytest.fail("/app/response.sh missing")
    r = subprocess.run([str(RESP), "999.999.999.999"], cwd="/app", capture_output=True, text=True, timeout=30)
    assert "invalid" in (r.stdout + r.stderr).lower()

def test_untested_block_rule_generated():
    # instruction: response.sh must "generate a corresponding block rule" for the IP (not checked officially)
    _, txt = _run_response()
    assert re.search(r"(iptables|ufw|nft|firewall-cmd|DROP|REJECT|deny|block)", txt, re.I) and BAD_IP in txt, "no block rule for the IP"

# DROPPED after calibration (rule 1: oracle fails it):
#   test_untested_incident_report_filename_pattern -- instruction: "incident_<IP>_<timestamp>.txt"; the reference
#   solution writes incident_report_<IP>_<YYYYmmdd_HHMMSS>.txt and the official test only looks for "incident" and the
#   IP in the file name. Observation for the paper: the reference solution does not follow the stated file-name pattern.
