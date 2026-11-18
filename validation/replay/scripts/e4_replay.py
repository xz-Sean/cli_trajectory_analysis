#!/usr/bin/env python3
"""E4 replayer: replay a failed trajectory prefix step-by-step inside the task's
Terminal-Bench container, snapshot after each step k, and test (a) official tests at
state S_k (progress) and (b) oracle-from-S_k (recoverability).

Usage:
  e4_replay.py build  <task>
  e4_replay.py replay <case_id> [--kmin K] [--kmax K] [--rep N] [--out DIR]
  e4_replay.py batch  <cases.json> [--jobs J]   (list of {"cid":..,"kmin":..,"kmax":..})
"""
import json, os, re, subprocess, sys, time, argparse, shlex, hashlib, difflib, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e4_recover import recover as recover_keystrokes

ROOT   = os.environ.get("E4_ROOT", os.getcwd())  # replay work dir, see validation/README.md
# optional shared package caches (uv/pip) mounted into replay + test containers: speeds up oracles that
# install heavy wheels at every snapshot (torch, transformers); does not change what is installed.
CACHE  = os.environ.get("E4_CACHE_DIR", os.path.join(ROOT, ".e4cache"))
def cache_mounts():
    if os.environ.get("E4_NO_CACHE"): return []
    for d in ("uv", "pip"): os.makedirs(os.path.join(CACHE, d), exist_ok=True)
    return ["-v", f"{CACHE}/uv:/root/.cache/uv", "-v", f"{CACHE}/pip:/root/.cache/pip", "-e", "UV_CACHE_DIR=/root/.cache/uv"]
# pre-built test virtualenv per task (see e4_prebake.py): mounted read-only into TEST containers only, at the path
# run-tests.sh expects, so the heavy `uv pip install` becomes a no-op. The agent-side replay container never sees it.
VENVS  = os.environ.get("E4_VENV_DIR", os.path.join(ROOT, ".e4venv"))
def venv_mount(task):
    if not task or os.environ.get("E4_NO_VENV"): return []
    meta = os.path.join(VENVS, task, "prebake.json")
    if not os.path.exists(meta): return []
    try: m = json.load(open(meta))
    except Exception: return []
    if not m.get("ok"): return []
    return ["-v", f"{VENVS}/{task}/venv:{m['path']}:ro"]
RAWTRAJ = os.path.join(ROOT, "merged_trajectories")
SPECIAL_KEY = re.compile(r"^(C-[a-zA-Z\[\]\\]|M-[a-zA-Z]|Enter|Escape|Tab|BSpace|Up|Down|Left|Right|Space|Home|End|PageUp|PageDown|F\d+)$")
TASKS  = os.path.join(ROOT, "resub/tb_tasks/terminal-bench/original-tasks")
CORPUS = os.path.join(ROOT, "trajrepair_extraction/corpus_RPO.json")
OUT    = os.path.join(ROOT, "resub/e4/runs")
STEP_TIMEOUT  = int(os.environ.get("E4_STEP_TIMEOUT", "600"))
TEST_TIMEOUT  = int(os.environ.get("E4_TEST_TIMEOUT", "900"))
OFFICIAL_TIMEOUT = int(os.environ.get("E4_OFFICIAL_TIMEOUT", str(TEST_TIMEOUT)))  # official-tests-only run (no oracle); shorter cap for tests that hang on agent code
IDLE_SECONDS  = 2.0   # terminus2: pane unchanged for this long => command finished

_corpus = None
def corpus():
    global _corpus
    if _corpus is None:
        _corpus = json.load(open(CORPUS))["tasks"]
    return _corpus

def sh(cmd, timeout=None, check=False, input=None):
    """run a command; on timeout kill the whole process group AND any docker container named in the command"""
    import signal
    p = subprocess.Popen(cmd, shell=isinstance(cmd, str), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE if input is not None else None, text=True, errors="replace",
                         start_new_session=True)
    try:
        out, err = p.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(p.pid, signal.SIGKILL)
        except Exception: pass
        # a `docker run --name X` / `docker exec X` keeps running in the daemon: kill the container too
        toks = cmd if isinstance(cmd, list) else cmd.split()
        for i, t in enumerate(toks):
            if t == "--name" and i + 1 < len(toks): subprocess.run(["docker", "rm", "-f", toks[i + 1]], capture_output=True)
            if t == "exec":
                # docker exec [opts] <container> ... : the container is the first token after exec not starting with '-' and not an option value
                j = i + 1
                while j < len(toks) and (toks[j].startswith("-") or toks[j-1] in ("-w", "-e", "-u")): j += 1
                if j < len(toks): subprocess.run(["docker", "exec", toks[j], "pkill", "-KILL", "-f", "sh -c"], capture_output=True)
        try: out, err = p.communicate(timeout=10)
        except Exception: out, err = "", ""
        raise
    p.stdout, p.stderr = out, err
    class R: pass
    r = R(); r.returncode = p.returncode; r.stdout = out; r.stderr = err
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed ({r.returncode}): {cmd}\n{err[-2000:]}")
    return r

def image_name(task): return f"e4/{task}"

def build(task):
    tdir = os.path.join(TASKS, task)
    if not os.path.isdir(tdir): raise SystemExit(f"no task dir {tdir}")
    ctx = tdir
    if not os.path.exists(os.path.join(tdir, "Dockerfile")):
        # some tasks keep the agent container under client/ (docker-compose build context)
        for cand in ("client", "app", "env"):
            if os.path.exists(os.path.join(tdir, cand, "Dockerfile")): ctx = os.path.join(tdir, cand); break
    p = sh(["docker", "build", "-q", "-t", image_name(task), ctx], timeout=3600)
    if p.returncode != 0:
        print(p.stderr[-3000:]); raise SystemExit(f"build failed for {task}")
    print("built", image_name(task), p.stdout.strip())

def parse_pytest(text):
    """return (passed, failed, total, names_passed) from pytest -rA output"""
    passed = re.findall(r"^PASSED\s+(\S+)", text, re.M)
    failed = re.findall(r"^FAILED\s+(\S+)", text, re.M)
    errors = re.findall(r"^ERROR\s+(\S+)", text, re.M)
    m = re.search(r"=+ (?:(\d+) passed)?(?:, )?(?:(\d+) failed)?", text)
    return {"passed": len(passed), "failed": len(failed) + len(errors),
            "total": len(passed) + len(failed) + len(errors),
            "passed_names": passed, "failed_names": failed + errors}

class Container:
    def __init__(self, task, cid, scaffold):
        self.task, self.cid, self.scaffold = task, cid, scaffold
        self.name = "e4_" + hashlib.md5(cid.encode()).hexdigest()[:10] + "_" + str(os.getpid())
    def start(self):
        sh(["docker", "rm", "-f", self.name])
        # PIP_BREAK_SYSTEM_PACKAGES compensates for PEP-668 drift: rebuilt images reject `pip install` into the system
        # python that the original (2025) runs allowed. Documented as a drift-compensation in the method.
        sh(["docker", "run", "-d", "--name", self.name, "-w", "/app", "-e", "PIP_BREAK_SYSTEM_PACKAGES=1", *cache_mounts(),
            "--entrypoint", "sleep", image_name(self.task), "infinity"], check=True)
        tdir = os.path.join(TASKS, self.task)
        sh(["docker", "exec", self.name, "mkdir", "-p", "/tests", "/oracle"], check=True)
        sh(f"docker cp {shlex.quote(tdir)}/tests/. {self.name}:/tests/", check=True)
        sh(f"docker cp {shlex.quote(tdir)}/run-tests.sh {self.name}:/tests/run-tests.sh", check=True)
        # speed/robustness: inject a static uv binary (no apt/curl needed), make run-tests.sh skip apt/curl when uv
        # exists, guard the `source $HOME/.local/bin/env` line, and pre-populate the uv cache with pytest.
        arch = sh(["docker", "exec", self.name, "uname", "-m"]).stdout.strip()
        uvbin = os.path.join(ROOT, "resub/tools", "uv-aarch64" if "aarch64" in arch or "arm64" in arch else "uv-x86_64")
        if os.path.exists(uvbin):
            sh(f"docker cp {shlex.quote(uvbin)} {self.name}:/usr/local/bin/uv", check=True)
            sh(["docker", "exec", self.name, "chmod", "+x", "/usr/local/bin/uv"])
        sh(["docker", "exec", self.name, "bash", "-c",
            "sed -i -E 's#^(\\s*)apt-get update#\\1command -v uv >/dev/null 2>\\&1 || apt-get update#; "
            "s#^(\\s*)apt-get install -y curl#\\1command -v uv >/dev/null 2>\\&1 || apt-get install -y curl#; "
            "s#^(\\s*)curl -LsSf https://astral.sh/uv/([^ ]+)/install.sh \\| sh#\\1command -v uv >/dev/null 2>\\&1 || curl -LsSf https://astral.sh/uv/\\2/install.sh | sh#; "
            "s#^(\\s*)source \\$HOME/.local/bin/env#\\1[ -f $HOME/.local/bin/env ] \\&\\& source $HOME/.local/bin/env#; "
            "s#^(\\s*)(uv venv|python3? -m venv) ([^ ]*tbench-testing[^ ]*)#\\1[ -d \\3 ] || \\2 \\3#' /tests/run-tests.sh; "
            "cd /tmp && uv venv .e4w >/dev/null 2>&1 && uv pip install --python .e4w pytest==8.4.1 >/dev/null 2>&1; rm -rf /tmp/.e4w; true"], timeout=600)
        sol = os.path.join(tdir, "solution.sh")
        self.has_oracle = os.path.exists(sol)
        if self.has_oracle:
            sh(f"docker cp {shlex.quote(sol)} {self.name}:/oracle/solution.sh", check=True)
        sub = os.path.join(ROOT, "resub/e4/subtests", self.task, "test_sub.py")
        self.has_sub = os.path.exists(sub)
        if self.has_sub:
            sh(["docker", "exec", self.name, "mkdir", "-p", "/subtests"], check=True)
            sh(f"docker cp {shlex.quote(sub)} {self.name}:/subtests/test_sub.py", check=True)
        if self.scaffold == "terminus2":
            r = sh(["docker", "exec", self.name, "bash", "-lc",
                    "command -v tmux >/dev/null || (apt-get update -qq && apt-get install -y -qq tmux) >/dev/null 2>&1; "
                    "tmux new-session -d -s main -x 220 -y 60 -c /app"], timeout=600)
            if r.returncode != 0: raise RuntimeError("tmux setup failed: " + r.stderr[-500:])
            time.sleep(1.0)
    def stop(self):
        sh(["docker", "rm", "-f", self.name])
    # ---- step execution ----
    def exec_step(self, P, step_index=None):
        at = P.get("action_type"); raw = P.get("raw_action") or ""
        if at in ("empty", "finish", None) and self.scaffold != "terminus2":
            return ""
        if self.scaffold == "miniswe":
            if at == "keystroke": return ""          # miniswe keystrokes are no-ops offline
            try:
                p = sh(["docker", "exec", "-w", "/app", self.name, "sh", "-c", raw], timeout=STEP_TIMEOUT)  # mini-swe runs actions via /bin/sh
                return (p.stdout + p.stderr)[-8000:]
            except subprocess.TimeoutExpired:
                return "<<E4 TIMEOUT>>"
        # terminus2: persistent tmux shell. Build the keystroke items for this step.
        items = self._items_for_step(P, step_index)
        before = self._pane()
        if not items:
            time.sleep(3.0); return self._pane_delta(before, self._pane())
        for it in items:
            ks = it["keystrokes"]
            if not ks: continue
            if not SPECIAL_KEY.match(ks.strip()) and not ks.endswith("\n"): ks = ks + "\n"
            if SPECIAL_KEY.match(ks.strip()):
                sh(["docker", "exec", self.name, "tmux", "send-keys", "-t", "main", ks.strip()])
            else:
                with tempfile.NamedTemporaryFile("w", delete=False, suffix=".keys") as f:
                    f.write(ks); tmp = f.name
                sh(f"docker cp {shlex.quote(tmp)} {self.name}:/tmp/e4_keys", check=True); os.unlink(tmp)
                sh(["docker", "exec", self.name, "tmux", "load-buffer", "-b", "e4", "/tmp/e4_keys"], check=True)
                sh(["docker", "exec", self.name, "tmux", "paste-buffer", "-b", "e4", "-t", "main", "-d"], check=True)
            time.sleep(min(float(it.get("duration") or 0.5), 30.0))
            self._wait_idle()
        return self._pane_delta(before, self._pane())
    def _items_for_step(self, P, step_index):
        at = P.get("action_type"); raw = P.get("raw_action") or ""
        if at == "bash": return [{"keystrokes": raw, "duration": 1.0}]
        if at == "keystroke": return [{"keystrokes": raw, "duration": 1.0}]
        if at in ("empty", None):
            # the raw export dropped the command for many devstral/gemini steps: recover from the model response
            f = os.path.join(RAWTRAJ, self.task, "terminus2", self.cid.split("__")[2], f"step_{step_index}.jsonl")
            try: aa = json.load(open(f)).get("agent_analysis") or ""
            except Exception: return []
            return recover_keystrokes(aa) or []
        return []
    @staticmethod
    def _pane_delta(before, after):
        """new screen content since `before` (terminus2 observations are deltas, not whole screens)"""
        b = before.rstrip("\n").split("\n"); a = after.rstrip("\n").split("\n")
        # find the longest suffix of `before` that is a prefix-aligned block inside `after`
        for n in range(min(len(b), len(a)), 0, -1):
            if a[:n] == b[-n:] or a[:n] == b[:n]:
                return "\n".join(a[n:])
        return after
    def _pane(self):
        p = sh(["docker", "exec", self.name, "tmux", "capture-pane", "-p", "-t", "main", "-S", "-200"])
        return p.stdout
    def _wait_idle(self):
        t0 = time.time(); last = self._pane(); last_change = time.time()
        while time.time() - t0 < STEP_TIMEOUT:
            time.sleep(0.5)
            cur = self._pane()
            if cur != last: last, last_change = cur, time.time()
            elif time.time() - last_change >= IDLE_SECONDS: return
    # ---- snapshot & evaluation ----
    def snapshot(self, k):
        tag = f"e4snap/{hashlib.md5(self.cid.encode()).hexdigest()[:10]}:{k}"
        sh(["docker", "commit", self.name, tag], check=True); return tag
    @staticmethod
    def run_tests(tag, with_oracle, task=None):
        pre = "cd /app && bash /oracle/solution.sh > /oracle/sol.log 2>&1; echo ORACLE_RC=$?; " if with_oracle else ""
        cmd = (pre + "cd /app && TEST_DIR=/tests bash /tests/run-tests.sh 2>&1 | tail -n 400; "
               "echo E4_SUBTESTS_BEGIN; if [ -f /subtests/test_sub.py ]; then cd /app && V=$(find /app -maxdepth 3 -type d -name .tbench-testing 2>/dev/null | head -1); source ${V:-/app/.tbench-testing}/bin/activate 2>/dev/null; "
               "python -m pytest /subtests/test_sub.py -rA -p no:cacheprovider 2>&1 | tail -n 200; fi")
        cname = "e4t_" + hashlib.md5((tag + str(time.time())).encode()).hexdigest()[:12]
        try:
            p = sh(["docker", "run", "--rm", "--name", cname, *cache_mounts(), *venv_mount(task), "--entrypoint", "bash", "-w", "/app", tag, "-c", cmd], timeout=(TEST_TIMEOUT if with_oracle else OFFICIAL_TIMEOUT))
            out = p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            sh(["docker", "rm", "-f", cname]); out = "<<E4 TEST TIMEOUT>>"
        off, _, subp = out.partition("E4_SUBTESTS_BEGIN")
        res = parse_pytest(off); res["raw_tail"] = off[-3000:]
        sp = parse_pytest(subp); res["sub"] = {}
        for cat in ("must", "mustnot", "untested"):
            pn = [n for n in sp["passed_names"] if f"::test_{cat}_" in n]; fn = [n for n in sp["failed_names"] if f"::test_{cat}_" in n]
            res["sub"][cat] = {"passed": len(pn), "failed": len(fn), "total": len(pn)+len(fn), "failed_names": fn}
        res["sub_raw_tail"] = subp[-1500:]
        m = re.search(r"ORACLE_RC=(\d+)", out); res["oracle_rc"] = int(m.group(1)) if m else None
        return res
    @staticmethod
    def drop(tag): sh(["docker", "rmi", "-f", tag])

def _norm_obs(x):
    x = x or ""
    x = re.sub(r"</?returncode>|</?output>|<returncode>\d+</returncode>", " ", x)   # mini-swe wrapper
    x = x.replace("COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT", "")
    return re.sub(r"\s+", " ", x).strip()[:2000]

def similarity(a, b):
    a = _norm_obs(a); b = _norm_obs(b)
    if not a and not b: return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()

def replay(cid, kmin=None, kmax=None, rep=0, out_dir=OUT):
    task, scaffold, model = cid.split("__")
    traj = corpus()[task]["trajectories"][cid]
    steps = traj["steps"]; m = len(steps)
    kmin = kmin or 1; kmax = min(kmax or m, m)
    os.makedirs(out_dir, exist_ok=True)
    outp = os.path.join(out_dir, f"{cid}__rep{rep}.json")
    rec = {"cid": cid, "task": task, "scaffold": scaffold, "model": model, "m": m,
           "kmin": kmin, "kmax": kmax, "rep": rep, "started": time.time(), "steps": [], "eval": {}}
    c = Container(task, cid, scaffold)
    c.start()
    try:
        # baseline: official tests on the pristine image (k=0) and oracle-from-pristine
        base = c.snapshot(0)
        rec["eval"]["0"] = {"tests": Container.run_tests(base, False, task),
                            "oracle": Container.run_tests(base, True, task) if c.has_oracle else None}
        Container.drop(base)
        for s in steps:
            k = s["i"]
            if k > kmax: break
            t0 = time.time(); out = c.exec_step(s["P"], s["i"])
            orig = (s["O"].get("raw_output") or s["O"].get("text") or "") if isinstance(s["O"], dict) else str(s["O"] or "")
            rec["steps"].append({"k": k, "type": s["P"].get("action_type"), "secs": round(time.time()-t0, 1),
                                 "out_sim": round(similarity(out, orig), 3), "out_tail": out[-600:]})
            if k >= kmin:
                tag = c.snapshot(k)
                ev = {"tests": Container.run_tests(tag, False, task)}
                ev["oracle"] = Container.run_tests(tag, True, task) if c.has_oracle else None
                Container.drop(tag)
                rec["eval"][str(k)] = ev
                json.dump(rec, open(outp, "w"), indent=1)
    finally:
        c.stop()
    rec["finished"] = time.time()
    json.dump(rec, open(outp, "w"), indent=1)
    return outp

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build"); b.add_argument("task")
    r = sub.add_parser("replay"); r.add_argument("cid"); r.add_argument("--kmin", type=int); r.add_argument("--kmax", type=int)
    r.add_argument("--rep", type=int, default=0); r.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if a.cmd == "build": build(a.task)
    elif a.cmd == "replay": print(replay(a.cid, a.kmin, a.kmax, a.rep, a.out))
    else: ap.print_help()

if __name__ == "__main__": main()
