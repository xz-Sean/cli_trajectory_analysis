# E4 sub-tests for vul-flink. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# The official run-tests.sh starts the built Flink cluster before pytest, so the REST API on
# localhost:8081 is reachable at sub-test time iff the distribution was rebuilt successfully.
import subprocess, http.client, json, socket, time, pytest
from pathlib import Path
SRC = Path("/opt/flink")
HANDLER = SRC / "flink-runtime/src/main/java/org/apache/flink/runtime/rest/FileUploadHandler.java"
DIST = SRC / "flink-dist/target/flink-1.11.2-bin/flink-1.11.2"

def _git(*args):
    return subprocess.run(["git", "-C", str(SRC), *args], capture_output=True, text=True)

def _rest_get(path):
    conn = http.client.HTTPConnection("localhost", 8081, timeout=5)
    conn.request("GET", path); r = conn.getresponse(); body = r.read(); conn.close()
    return r.status, body

def _rest_up(tries=5):
    for _ in range(tries):
        try:
            st, _ = _rest_get("/jars")
            if 200 <= st < 300: return True
        except (OSError, socket.timeout): pass
        time.sleep(1)
    return False

def _upload(filename, content=b"success"):
    boundary = "----E4SubBoundary"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"jarfile\"; filename=\"{filename}\"\r\n\r\n").encode() \
           + content + f"\r\n--{boundary}--\r\n".encode()
    conn = http.client.HTTPConnection("localhost", 8081, timeout=10)
    conn.request("POST", "/jars/upload", body=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                                            "Content-Length": str(len(body)), "Connection": "close"})
    r = conn.getresponse(); data = r.read(); conn.close()
    return r.status, data

def test_must_fix_is_in_source_code():
    # "fix must be in source code": some java source under flink-runtime differs from the checked-in tree
    assert HANDLER.exists()
    changed = _git("diff", "--name-only", "HEAD").stdout.split()
    assert any(p.startswith("flink-runtime/src/main/java/") and p.endswith(".java") for p in changed), changed

def test_must_distribution_rebuilt():
    # "rebuild the Flink distribution so the runtime jars include the fix"
    assert (DIST / "bin/start-cluster.sh").exists()
    assert list((DIST / "lib").glob("flink-dist_*.jar"))

def test_must_traversal_upload_does_not_create_file():
    assert _rest_up(), "Flink REST not reachable on localhost:8081 (distribution not built/started)"
    target = Path("/tmp/e4_sub_traversal")
    if target.exists(): target.unlink()
    _upload("../../../../../../tmp/e4_sub_traversal")
    time.sleep(2)
    assert not target.exists(), "path traversal via Content-Disposition filename still writes outside the upload dir"

def test_must_no_tmp_success_left_by_official_probe():
    # the official test uploads filename ../../../../../../tmp/success; it must not exist afterwards
    assert not Path("/tmp/success").exists()

def test_mustnot_source_tree_removed():
    assert (SRC / ".git").is_dir() and HANDLER.exists()

def test_mustnot_source_files_deleted():
    deleted = [l for l in _git("status", "--porcelain").stdout.splitlines()
               if l[:2].strip() == "D" and "flink-runtime/src/main/" in l]
    assert not deleted, deleted

def test_mustnot_rest_api_behaviour_changed():
    if not _rest_up(): pytest.skip("REST not reachable; nothing to check")
    st, body = _rest_get("/jars")
    assert st == 200
    d = json.loads(body); assert "files" in d and "address" in d

def test_untested_normal_upload_still_works():
    # "Normal uploads (without path components in the filename) continue to work as before"
    assert _rest_up(), "Flink REST not reachable on localhost:8081"
    st, data = _upload("e4_sub_normal.jar")
    assert st == 200, (st, data[:300])
    d = json.loads(data)
    assert d.get("status") == "success" and d.get("filename", "").endswith("e4_sub_normal.jar"), d
