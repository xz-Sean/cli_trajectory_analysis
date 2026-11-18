# E4 sub-tests for create-bucket. State assertions only (state lives inside the running LocalStack process).
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import json, socket, subprocess, pytest
EP = "http://localhost:4566"; B = "sample-bucket"
ALL_USERS = "http://acs.amazonaws.com/groups/global/AllUsers"

def _s3():
    try:
        import boto3
        return boto3.client("s3", endpoint_url=EP, aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    except ImportError:
        pytest.skip("boto3 unavailable")

def _grants():
    s3 = _s3()
    try: return s3.get_bucket_acl(Bucket=B).get("Grants", [])
    except Exception: return []

def _policy_public_read():
    s3 = _s3()
    try: pol = json.loads(s3.get_bucket_policy(Bucket=B)["Policy"])
    except Exception: return False
    for st in pol.get("Statement", []):
        acts = st.get("Action", []); acts = [acts] if isinstance(acts, str) else acts
        res = st.get("Resource", []); res = [res] if isinstance(res, str) else res
        pr = st.get("Principal"); pub = pr == "*" or (isinstance(pr, dict) and pr.get("AWS") in ("*", ["*"]))
        if st.get("Effect") == "Allow" and pub and any(a in ("s3:GetObject", "s3:*") for a in acts) and any(r.endswith(f":::{B}/*") for r in res):
            return True
    return False

# ---------------- MUST ----------------
def test_must_bucket_exists():
    names = [b["Name"] for b in _s3().list_buckets().get("Buckets", [])]
    assert B in names, names

def test_must_bucket_public_read():
    acl_ok = any(g.get("Grantee", {}).get("URI") == ALL_USERS and g.get("Permission") in ("READ", "FULL_CONTROL") for g in _grants())
    assert acl_ok or _policy_public_read(), "sample-bucket is not publicly readable (no AllUsers READ grant, no public GetObject policy)"

# ---------------- MUSTNOT ----------------
def test_mustnot_localstack_not_reachable():
    # the S3 endpoint (localstack on 4566) must still be up; nothing else in this image is load-bearing
    with socket.create_connection(("localhost", 4566), timeout=5): pass

def test_mustnot_bucket_publicly_writable():
    grants = _grants()
    if not grants: pytest.skip("no bucket / no ACL yet")
    assert not any(g.get("Grantee", {}).get("URI") == ALL_USERS and g.get("Permission") in ("WRITE", "WRITE_ACP", "FULL_CONTROL") for g in grants), \
        "public-read requested, but AllUsers were granted write"

# UNTESTED: none -- the official tests cover bucket existence and public read (ACL or policy); the instruction
# states nothing else (no region/ownership/versioning requirements).
