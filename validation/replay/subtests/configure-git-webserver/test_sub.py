# E4 sub-tests for configure-git-webserver. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# NOTE: running daemons do not survive a docker-commit snapshot, so the 8080 check accepts either a live
# listener or on-disk server configuration; the deploy check drives the hook through a local (file://) push.
import os, re, shutil, subprocess, tempfile, time, uuid, pytest
from pathlib import Path
REPO = Path("/git/server")
_state = {}

def _env():
    # the repo is normally owned by the ssh user while these tests run as root: give every git process in the
    # chain (clone/push/upload-pack/receive-pack/hook) a throw-away HOME whose .gitconfig trusts the repo
    if "home" not in _state:
        h = tempfile.mkdtemp(prefix="e4home_"); _state["home"] = h
        Path(h, ".gitconfig").write_text("[safe]\n\tdirectory = *\n[user]\n\temail = e4@example.com\n\tname = e4\n[init]\n\tdefaultBranch = master\n")
    return {**os.environ, "HOME": _state["home"]}

def _sh(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=50, env=_env())

def _listening_8080():
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            for line in Path(f).read_text().splitlines()[1:]:
                parts = line.split()
                if parts[1].endswith(":1F90") and parts[3] == "0A": return True
        except OSError: pass
    return False

def _push_probe():
    """clone /git/server, commit hello.html + a unique probe file on master, push; return probe name"""
    if "probe" in _state: return _state["probe"]
    probe = f"e4probe_{uuid.uuid4().hex[:10]}.html"; _state["probe"] = probe
    d = tempfile.mkdtemp(prefix="e4clone_"); _state["clone"] = d
    git = "git"
    r = _sh(f"{git} clone -q {REPO} {d}/w && cd {d}/w && ({git} checkout -q master 2>/dev/null || {git} checkout -q -b master)"
            f" && echo 'hello world' > hello.html && echo 'hello world' > {probe} && {git} add -A && {git} commit -q -m 'add hello.html'"
            f" && {git} push -q origin master")
    _state["push"] = r
    return probe

def _deployed_dirs():
    """directories outside our clone that received the probe file (i.e. the push hook deployed the tree)"""
    probe = _push_probe()
    r = _sh(f"find / -xdev \\( -path /proc -o -path /sys -o -path /dev -o -path {_state['clone']} \\) -prune -o -name {probe} -print 2>/dev/null")
    return [Path(p).parent for p in r.stdout.split() if p]

# ---------------- MUST ----------------
def test_must_git_repo_at_git_server():
    assert shutil.which("git"), "git not installed"
    assert REPO.exists() and _sh(f"git -C {REPO} rev-parse --git-dir").returncode == 0, "/git/server is not a git repository"

def test_must_push_to_master_is_accepted():
    if not shutil.which("git") or not REPO.exists(): pytest.skip("no git / no repo")
    _push_probe(); r = _state["push"]
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]

def test_must_push_deploys_hello_html_to_webroot():
    if not shutil.which("git") or not REPO.exists(): pytest.skip("no git / no repo")
    dirs = _deployed_dirs()
    assert dirs, "pushed files were not deployed anywhere outside the clone (no post-receive deployment)"
    assert any((d/"hello.html").is_file() and (d/"hello.html").read_text().strip() == "hello world" for d in dirs), dirs

def test_must_webserver_on_port_8080():
    if _listening_8080(): return
    # snapshot fallback: some web-server configuration / launcher on disk must bind 8080
    # (nginx "listen 8080", apache "Listen 8080", lighttpd server.port, caddy ":8080", python -m http.server 8080, --port 8080)
    pat = r"^\s*(listen|Listen)\s+([0-9.*:\[\]]*:)?8080\b|server\.port\s*=\s*8080|http\.server\s+8080\b|(-p|--port|-l|--listen)[ =]+8080\b|^\s*:8080\s*\{"
    r = _sh(f"grep -rlsE '{pat}' /etc/nginx /etc/apache2 /etc/httpd /etc/lighttpd /etc/caddy /etc/supervisor /etc/systemd/system "
            "/etc/init.d /etc/rc.local /git /srv /var/www /usr/local/bin /root/*.sh /app/*.sh 2>/dev/null | head -5")
    assert r.stdout.strip(), "nothing listens on 8080 and no web-server config for port 8080 found"

# ---------------- MUSTNOT ----------------
def test_mustnot_ssh_server_missing():
    # "git clone user@server:/git/server" from another machine needs an ssh daemon installed on the server
    assert shutil.which("sshd") or Path("/usr/sbin/sshd").exists(), "no sshd installed"

def test_mustnot_deployed_hello_html_outside_served_root():
    # the deployed copy must live under the directory the web server is configured to serve (when we can tell)
    if not shutil.which("git") or not REPO.exists(): pytest.skip("no git / no repo")
    dirs = _deployed_dirs()
    if not dirs: pytest.skip("nothing deployed")
    r = _sh("grep -rhsoE '^\\s*root\\s+[^;]+;|DocumentRoot\\s+\\S+|server\\.document-root\\s*=\\s*\"[^\"]+\"' /etc/nginx /etc/apache2 /etc/httpd /etc/lighttpd 2>/dev/null")
    roots = [Path(x) for x in re.findall(r"(/[^\s;\"]+)", r.stdout)]
    if not roots: pytest.skip("web root not discoverable from config")
    assert any(str(d).startswith(str(root)) for d in dirs for root in roots), (dirs, roots)

# ---------------- UNTESTED ----------------
def test_untested_hook_deploys_whole_tree_not_only_hello_html():
    # a push must publish the pushed tree (the user may push other files later); official only checks hello.html
    if not shutil.which("git") or not REPO.exists(): pytest.skip("no git / no repo")
    dirs = _deployed_dirs()
    assert dirs and all((d/_state["probe"]).read_text().strip() == "hello world" for d in dirs)
