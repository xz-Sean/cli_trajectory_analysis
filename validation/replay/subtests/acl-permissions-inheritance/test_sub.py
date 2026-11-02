# E4 sub-tests for acl-permissions-inheritance. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import grp, os, pwd, subprocess, uuid, pytest
D = "/srv/shared"

def _sh(cmd):
    return subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)

def _acl():
    if not os.path.isdir(D): pytest.fail(f"{D} missing")
    out = _sh(f"getfacl -p {D}").stdout
    return {ln.split()[0] for ln in out.splitlines() if ln.strip() and not ln.startswith("#")}

def test_must_directory_group_and_mode_2770():
    assert os.path.isdir(D), f"{D} missing"
    st = os.stat(D)
    assert grp.getgrgid(st.st_gid).gr_name == "research", "group is not research"
    assert st.st_mode & 0o7777 == 0o2770, oct(st.st_mode & 0o7777)

def test_must_current_acl_entries():
    acl = _acl()
    for e in ("group:research:rwx", "user:alice:rwx", "user:bob:rwx", "other::---"):
        assert e in acl, f"missing {e}; have {sorted(acl)}"

def test_must_default_acl_entries():
    acl = _acl()
    for e in ("default:group:research:rwx", "default:user:alice:rwx", "default:user:bob:rwx", "default:mask::rwx", "default:other::---"):
        assert e in acl, f"missing {e}; have {sorted(acl)}"

def test_must_alice_file_accessible_by_bob_and_inherits_acl():
    if not os.path.isdir(D): pytest.fail(f"{D} missing")
    f = f"{D}/e4_{uuid.uuid4().hex[:8]}.txt"
    try:
        assert _sh(f"runuser -u alice -- bash -lc 'echo hi > {f}'").returncode == 0, "alice cannot create a file"
        r = _sh(f"runuser -u bob -- bash -lc 'cat {f} && echo more >> {f}'")
        assert r.returncode == 0 and "hi" in r.stdout, f"bob cannot read/write alice's file: {r.stderr}"
        assert grp.getgrgid(os.stat(f).st_gid).gr_name == "research", "setgid inheritance failed"
        acl = {ln.split()[0] for ln in _sh(f"getfacl -p {f}").stdout.splitlines() if ln.strip() and not ln.startswith("#")}
        assert {"user:alice:rwx", "user:bob:rwx", "group:research:rwx", "other::---"} <= acl, sorted(acl)
    finally:
        _sh(f"rm -f {f}")

def test_must_outside_user_denied():
    if not os.path.isdir(D): pytest.fail(f"{D} missing")
    r = _sh(f"runuser -u nobody -- bash -lc 'ls {D}'")       # nobody is not in research
    assert r.returncode != 0 and "Permission denied" in r.stderr, r

def test_mustnot_files_created_in_shared_dir():
    # instruction: "Do NOT create any files in the directory"
    if not os.path.isdir(D): pytest.skip("directory not created yet")
    assert os.listdir(D) == [], os.listdir(D)

def test_mustnot_users_or_group_broken():
    assert grp.getgrnam("research") and pwd.getpwnam("alice") and pwd.getpwnam("bob")
    for u in ("alice", "bob"):
        assert "research" in [g.gr_name for g in grp.getgrall() if u in g.gr_mem], f"{u} no longer in research"

def test_untested_current_mask_allows_full_permissions():
    # instruction: "Set proper mask to allow full permissions" -- official tests only check the *default* mask
    assert "mask::rwx" in _acl()
