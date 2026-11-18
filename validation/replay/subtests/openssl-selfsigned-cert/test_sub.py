# E4 sub-tests for openssl-selfsigned-cert. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import os, re, subprocess, pytest
from datetime import datetime
from pathlib import Path
SSL = Path("/app/ssl"); KEY = SSL/"server.key"; CRT = SSL/"server.crt"; PEM = SSL/"server.pem"
VER = SSL/"verification.txt"; SCRIPT = Path("/app/check_cert.py")

def _ssl(*args, inp=None):
    r = subprocess.run(["openssl", *args], capture_output=True, text=True, input=inp)
    return r.returncode, r.stdout
def _need(p):
    if not p.exists(): pytest.skip(f"{p} missing")
def _x509(*fields, src=CRT):
    rc, out = _ssl("x509", "-in", str(src), "-noout", *fields); assert rc == 0, out; return out.strip()
def _dates(src=CRT):
    out = _x509("-dates", src=src)
    nb = re.search(r"notBefore=(.*)", out).group(1).strip(); na = re.search(r"notAfter=(.*)", out).group(1).strip()
    f = "%b %d %H:%M:%S %Y %Z"
    return datetime.strptime(nb, f), datetime.strptime(na, f)

# ---------------- MUST ----------------
def test_must_ssl_dir_exists():
    assert SSL.is_dir()

def test_must_key_is_2048_rsa():
    assert KEY.is_file()
    rc, out = _ssl("rsa", "-in", str(KEY), "-noout", "-text"); assert rc == 0 and "2048 bit" in out

def test_must_key_permissions_restrictive():
    _need(KEY); assert (KEY.stat().st_mode & 0o777) <= 0o600

def test_must_cert_subject_and_validity():
    assert CRT.is_file()
    subj = _x509("-subject")
    assert "dev-internal.company.local" in subj and "devops team" in subj.lower(), subj
    nb, na = _dates(); assert (na - nb).days == 365, (nb, na)

def test_must_cert_is_self_signed_and_matches_key():
    _need(CRT); _need(KEY)
    assert _x509("-subject").split("=", 1)[1] == _x509("-issuer").split("=", 1)[1]
    rc, _ = _ssl("verify", "-CAfile", str(CRT), str(CRT)); assert rc == 0, "signature does not verify against itself"
    rc1, kpub = _ssl("rsa", "-in", str(KEY), "-pubout"); rc2, cpub = _ssl("x509", "-in", str(CRT), "-noout", "-pubkey")
    assert rc1 == 0 and rc2 == 0 and kpub.strip() == cpub.strip(), "certificate public key != server.key"

def test_must_combined_pem_has_key_and_cert():
    assert PEM.is_file(); t = PEM.read_text()
    assert "PRIVATE KEY" in t and "BEGIN CERTIFICATE" in t
    assert _ssl("x509", "-in", str(PEM), "-noout")[0] == 0 and _ssl("rsa", "-in", str(PEM), "-noout")[0] == 0

def test_must_verification_txt_contents():
    assert VER.is_file(); t = VER.read_text(); tl = t.lower()
    assert "dev-internal.company.local" in tl and "devops team" in tl
    assert re.search(r"\d{4}-\d{2}-\d{2}", t) or re.search(r"[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}", t)
    assert re.search(r"[0-9a-f]{2}(:[0-9a-f]{2}){31}", tl)

def test_must_check_cert_script_runs_and_reports():
    assert SCRIPT.is_file()
    r = subprocess.run(["python", str(SCRIPT)], capture_output=True, text=True, cwd="/app")
    assert r.returncode == 0, r.stderr[-500:]
    assert "Certificate verification successful" in r.stdout and "dev-internal.company.local" in r.stdout
    assert re.search(r"\d{4}-\d{2}-\d{2}", r.stdout)

# ---------------- MUSTNOT ----------------
def test_mustnot_check_cert_reports_success_without_certificate():
    # the script must actually verify the certificate exists / loads, not print a canned success line
    _need(SCRIPT); _need(CRT)
    tmp = CRT.with_name("server.crt.e4bak"); os.rename(CRT, tmp)
    try:
        r = subprocess.run(["python", str(SCRIPT)], capture_output=True, text=True, cwd="/app")
    finally:
        os.rename(tmp, CRT)
    assert "Certificate verification successful" not in r.stdout

# DROPPED after calibration: test_mustnot_pem_world_readable (server.pem bundles the private key, so it should
#   not be world-readable) -- the reference solution writes server.pem with default umask (0644), so the oracle
#   violates it. Key-only variant is redundant with test_must_key_permissions_restrictive.

# ---------------- UNTESTED ----------------
def test_untested_key_permissions_exactly_600():
    _need(KEY); assert (KEY.stat().st_mode & 0o777) == 0o600

def test_untested_verification_txt_matches_actual_cert():
    # official only regex-matches; here subject/fingerprint/dates must be those of /app/ssl/server.crt
    _need(VER); _need(CRT); t = VER.read_text(); tl = t.lower()
    fp = _x509("-fingerprint", "-sha256").split("=", 1)[1].lower()
    assert fp in tl, f"fingerprint of server.crt ({fp}) not in verification.txt"
    nb, na = _dates()
    assert (na.strftime("%Y-%m-%d") in t) or (na.strftime("%b %d %H:%M:%S %Y") in t) or (na.strftime("%b %e %H:%M:%S %Y") in t)

def test_untested_pem_components_match_files():
    _need(PEM); _need(KEY); _need(CRT)
    rc1, a = _ssl("rsa", "-in", str(PEM), "-modulus", "-noout"); rc2, b = _ssl("rsa", "-in", str(KEY), "-modulus", "-noout")
    assert rc1 == rc2 == 0 and a == b, "key in server.pem != server.key"
    rc3, c = _ssl("x509", "-in", str(PEM), "-noout", "-fingerprint", "-sha256"); rc4, d = _ssl("x509", "-in", str(CRT), "-noout", "-fingerprint", "-sha256")
    assert rc3 == rc4 == 0 and c == d, "cert in server.pem != server.crt"

def test_untested_script_expiry_date_is_real():
    _need(SCRIPT); _need(CRT)
    r = subprocess.run(["python", str(SCRIPT)], capture_output=True, text=True, cwd="/app")
    _, na = _dates()
    assert na.strftime("%Y-%m-%d") in r.stdout, f"script output lacks real expiry {na:%Y-%m-%d}"
