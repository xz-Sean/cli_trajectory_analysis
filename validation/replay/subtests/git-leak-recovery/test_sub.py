# E4 sub-tests for git-leak-recovery. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import subprocess, os
from pathlib import Path
REPO = "/app/repo"; SECRET = "secret[lost_and_found_in_git]"
INIT_MSG = "chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc"
# reachable history in the pristine image (HEAD first); challenge-setup.sh never rewrote these
PRISTINE_HEAD_CHAIN = ["f791a600a96d82294492998ea75e23cdcea39e0b", "f126b51add6ce732b40bfe96ad2f98f46cd977dd"]

def git(*a, **kw):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, timeout=30, **kw)

def test_must_secret_txt_has_recovered_secret():
    p = Path("/app/secret.txt"); assert p.is_file()
    assert p.read_text().strip() == SECRET, p.read_text()

def test_must_no_secret_in_reachable_history():
    r = git("log", "--all", "-p", "-S", "secret["); assert r.returncode == 0, r.stderr
    assert "secret[" not in r.stdout
    r = git("log", "--all", "--grep", "secret\\["); assert not r.stdout.strip()

def test_must_no_secret_in_any_git_object():
    # every object still in the object store (loose or packed, reachable or not)
    r = subprocess.run(["git", "-C", REPO, "cat-file", "--batch-all-objects", "--batch"], capture_output=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert b"secret[" not in r.stdout

def test_must_no_secret_in_unreachable_objects():
    r = git("fsck", "--unreachable", "--no-reflogs"); assert r.returncode == 0, r.stderr
    for line in r.stdout.splitlines():
        if line.startswith("unreachable") or line.startswith("dangling"):
            h = line.split()[-1]; c = git("cat-file", "-p", h)
            assert "secret[" not in c.stdout, line

def test_must_commit_messages_and_files_untouched():
    r = git("log", "--format=%s", "HEAD"); assert r.returncode == 0, r.stderr
    assert r.stdout.split("\n")[:2] == [INIT_MSG, INIT_MSG], r.stdout
    assert Path(REPO, "README.md").read_text() == "demo project\nsome changes\n"

def test_mustnot_repo_removed_or_reinitialised():
    assert os.path.isdir(REPO + "/.git")
    r = git("rev-list", "--count", "HEAD"); assert r.stdout.strip() == "2", r.stdout
    assert set(os.listdir(REPO)) == {".git", "README.md"}, os.listdir(REPO)

def test_mustnot_secret_string_in_repo_dir_raw():
    # "cannot be found anywhere in that repo": byte scan of every file incl. .git (loose objects are zlib, so
    # this catches plaintext copies: reflogs, lost-found, packed-refs, notes, stray files)
    hits = []
    for dp, dn, fn in os.walk(REPO):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                if b"secret[" in Path(p).read_bytes(): hits.append(p)
            except OSError: pass
    assert not hits, hits

def test_untested_reachable_commit_hashes_unchanged():
    # "irrelevant files and commit messages remain untouched": the two good commits need no rewriting
    r = git("rev-list", "HEAD"); assert r.stdout.split() == PRISTINE_HEAD_CHAIN, r.stdout
