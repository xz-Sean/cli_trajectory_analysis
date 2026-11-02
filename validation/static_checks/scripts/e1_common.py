"""Shared helpers for the E1 objective-validation suite (E1.1-E1.4).

Only the Python standard library is used.  Nothing here writes to the data
directories; all outputs go to resub/e1/.

Trajectory format notes (merged_trajectories/<task>/<scaffold>/<model>/step_N.jsonl):
  * one JSON object per file: task_id, step_index, command, agent_analysis,
    terminal_result (+ llm_analysis / raw_llm_response, which are IGNORED).
  * miniswe   : command is bash; terminal_result is often wrapped as
                <returncode>N</returncode><output>...</output>.
  * openhands : command is bash or a tool wrapper (TOOL_CALL finish(...),
                TOOL think, TOOL_CALL task_tracker(...), TOOL_CALL
                execute_ipython_cell(...), EDITOR_STR_REPLACE/CREATE/INSERT/UNDO_EDIT(...));
                agent_analysis usually starts with "Command `...` executed with exit code N."
  * terminus2 : for devstral/gemini the `command` field is EMPTY and the raw model
                response (Gemini API JSON or a fenced ```json block with keys
                analysis/plan/commands[].keystrokes/task_complete) sits in
                agent_analysis; terminal_result is the tmux screen which echoes
                the commands after a `user@host:cwd#` prompt.  We recover the
                command list from the JSON when parseable, otherwise from the
                prompt-echo lines.
"""
import functools
import json
import os
import re

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # package root
TRAJ_DIR = os.environ.get('TRAJ_DIR', os.path.join(PKG, 'merged_trajectories'))  # raw trajectories (released separately)
ANN_PATH = os.path.join(PKG, 'data', 'traj_data_v2_all89tasks.json')
OUT_DIR = os.path.join(PKG, 'validation', 'static_checks')

SCAFFOLDS = ['miniswe', 'openhands', 'terminus2']
MODELS = ['claude', 'deepseek-v3.2', 'devstral', 'gemini', 'gpt5', 'kimi', 'qwen']


def load_annotations():
    with open(ANN_PATH) as fh:
        return json.load(fh)


def is_fail(rec):
    return 't_err' in rec


def split_case(case_id):
    task, scaffold, model = case_id.split('__')
    return task, scaffold, model


# ---------------------------------------------------------------------------
# terminus2 raw-response recovery
# ---------------------------------------------------------------------------
PROMPT_LINE_RE = re.compile(r'^[\w.-]+@[\w.-]+:[^\n]*?[#$]\s?(.*)$', re.M)
FENCE_RE = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.S)
KEYSTROKE_RE = re.compile(r'"keystrokes"\s*:\s*"((?:[^"\\]|\\.)*)"')
TC_RE = re.compile(r'"task_complete"\s*:\s*(true|false)', re.I)
ANALYSIS_RE = re.compile(r'"analysis"\s*:\s*"((?:[^"\\]|\\.)*)"')
PLAN_RE = re.compile(r'"plan"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _json_unescape(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s.replace('\\n', '\n').replace('\\"', '"')


def parse_terminus_response(analysis_raw):
    """Return dict(analysis, plan, commands:list[str], task_complete:bool|None) or None."""
    txt = analysis_raw or ''
    if not txt.strip():
        return None
    # Gemini API wrapper -> join text parts
    if txt.lstrip().startswith('{'):
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict) and 'candidates' in obj:
                parts = []
                for c in obj.get('candidates', []):
                    for p in (c.get('content') or {}).get('parts', []):
                        parts.append(p.get('text', ''))
                txt = '\n'.join(parts)
            elif isinstance(obj, dict) and ('commands' in obj or 'task_complete' in obj or 'analysis' in obj):
                return _norm_t2(obj)
        except Exception:
            pass
    m = FENCE_RE.search(txt)
    cand = m.group(1) if m else None
    if cand is None:
        s, e = txt.find('{'), txt.rfind('}')
        if s >= 0 and e > s:
            cand = txt[s:e + 1]
    if cand:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and ('commands' in obj or 'task_complete' in obj or 'analysis' in obj):
                return _norm_t2(obj)
        except Exception:
            pass
    # regex fallback on possibly-truncated JSON
    keys = KEYSTROKE_RE.findall(txt)
    tc = TC_RE.search(txt)
    an = ANALYSIS_RE.search(txt)
    pl = PLAN_RE.search(txt)
    if keys or tc or an:
        return {
            'analysis': _json_unescape(an.group(1)) if an else '',
            'plan': _json_unescape(pl.group(1)) if pl else '',
            'commands': [_json_unescape(k) for k in keys],
            'task_complete': (tc.group(1).lower() == 'true') if tc else None,
        }
    return None


def _norm_t2(obj):
    cmds = []
    for c in obj.get('commands') or []:
        if isinstance(c, dict):
            cmds.append(str(c.get('keystrokes', '')))
        elif isinstance(c, str):
            cmds.append(c)
    tc = obj.get('task_complete')
    return {
        'analysis': str(obj.get('analysis', '') or ''),
        'plan': str(obj.get('plan', '') or ''),
        'commands': cmds,
        'task_complete': bool(tc) if tc is not None else None,
    }


def prompt_echo_commands(terminal_raw):
    out = []
    for m in PROMPT_LINE_RE.finditer(terminal_raw or ''):
        c = m.group(1).strip()
        if c:
            out.append(c)
    return out


def strip_prompt_lines(terminal_raw):
    return PROMPT_LINE_RE.sub('', terminal_raw or '')


# ---------------------------------------------------------------------------
# per-scaffold output normalisation
# ---------------------------------------------------------------------------
MS_WRAP_RE = re.compile(r'^\s*<returncode>(-?\d+)</returncode>\s*<output>(.*)</output>\s*$', re.S)
OH_EXIT_RE = re.compile(r'executed with exit code (-?\d+)')
T2_NOCMD_MARK = '(command not found in terminal output)'
T2_NOOUT_MARK = '(command executed successfully with no output)'


def normalise_step(raw, scaffold):
    cmd_raw = raw.get('command') or ''
    ana_raw = raw.get('agent_analysis') or ''
    ter_raw = raw.get('terminal_result') or ''
    step = {
        'i': int(raw.get('step_index') or 0),
        'command_raw': cmd_raw,
        'analysis_raw': ana_raw,
        'terminal_raw': ter_raw,
        'command': cmd_raw.strip(),
        'analysis': ana_raw,
        'terminal': ter_raw,
        'output': ter_raw,
        'exit_code': None,
        'task_complete': False,
        'recovered_from': None,
    }
    if scaffold == 'miniswe':
        m = MS_WRAP_RE.match(ter_raw)
        if m:
            step['exit_code'] = int(m.group(1))
            step['output'] = m.group(2)
    elif scaffold == 'openhands':
        m = OH_EXIT_RE.search(ana_raw[:300])
        if m:
            step['exit_code'] = int(m.group(1))
        if cmd_raw.startswith('TOOL think'):
            # the thought itself is in terminal_result
            step['analysis'] = ter_raw
    elif scaffold == 'terminus2':
        parsed = parse_terminus_response(ana_raw)
        if parsed:
            step['analysis'] = (parsed['analysis'] + '\n' + parsed['plan']).strip() or ana_raw
            if parsed['task_complete']:
                step['task_complete'] = True
            if not step['command'] and parsed['commands']:
                step['command'] = '\n'.join(c.strip() for c in parsed['commands'] if c.strip())
                step['recovered_from'] = 'json'
        else:
            if re.search(r'task_complete\W{0,4}true', ana_raw, re.I):
                step['task_complete'] = True
        if not step['command']:
            echo = prompt_echo_commands(ter_raw)
            if echo:
                step['command'] = '\n'.join(echo)
                step['recovered_from'] = 'prompt_echo'
        out = strip_prompt_lines(ter_raw)
        step['keystroke_sent'] = bool(step['command']) or (T2_NOCMD_MARK in ter_raw) or (T2_NOOUT_MARK in ter_raw) or bool(out.strip())
        for mark in (T2_NOCMD_MARK, T2_NOOUT_MARK):
            out = out.replace(mark, '')
        step['output'] = out
    step['all_text'] = '\n'.join([cmd_raw, ana_raw, ter_raw])
    return step


@functools.lru_cache(maxsize=None)
def load_traj(case_id):
    """Return (steps, missing_steps).  steps is a list indexed 0..m-1 (step i -> steps[i-1]).
    Missing files yield a placeholder step with empty fields and are listed in missing_steps."""
    task, scaffold, model = split_case(case_id)
    d = os.path.join(TRAJ_DIR, task, scaffold, model)
    files = {}
    if os.path.isdir(d):
        for fn in os.listdir(d):
            m = re.match(r'step_(\d+)\.jsonl$', fn)
            if m:
                files[int(m.group(1))] = os.path.join(d, fn)
    n = max(files) if files else 0
    steps, missing = [], []
    for i in range(1, n + 1):
        if i not in files:
            missing.append(i)
            steps.append(normalise_step({'step_index': i}, scaffold))
            continue
        try:
            with open(files[i]) as fh:
                raw = json.loads(fh.readline())
        except Exception:
            missing.append(i)
            steps.append(normalise_step({'step_index': i}, scaffold))
            continue
        steps.append(normalise_step(raw, scaffold))
    return steps, missing


# ---------------------------------------------------------------------------
# command-level action classifier (E1.4; also used by E1.1 weak signal and E1.3)
# ---------------------------------------------------------------------------
E_FIRST_TOKENS = {
    'ls', 'cat', 'head', 'tail', 'find', 'grep', 'egrep', 'fgrep', 'rg', 'ag', 'which', 'pwd',
    'less', 'more', 'tree', 'stat', 'file', 'wc', 'type', 'whereis', 'locate', 'du', 'df',
    'env', 'printenv', 'man', 'cd', 'realpath', 'readlink', 'id', 'whoami', 'uname', 'hostname',
    'nproc', 'free', 'lscpu', 'lsblk', 'ps', 'getent', 'strings', 'nl', 'od', 'xxd', 'hexdump',
    'basename', 'dirname', 'date', 'history', 'jobs',
}
E_SUBCMD = {
    'git': {'status', 'log', 'show', 'branch', 'remote', 'ls-files', 'ls-tree', 'rev-parse', 'describe', 'tag', 'blame', 'config'},
    'pip': {'list', 'show', 'freeze'}, 'pip3': {'list', 'show', 'freeze'},
    'docker': {'ps', 'images', 'inspect', 'logs'}, 'npm': {'ls', 'list', 'view'},
    'cargo': {'tree', 'metadata'}, 'go': {'env', 'version', 'list'}, 'conda': {'info', 'list', 'env'},
    'apt': {'list', 'show', 'search'}, 'apt-cache': {'search', 'show', 'policy'}, 'dpkg': {'-l', '-L', '-s'},
    'systemctl': {'status'}, 'ip': {'addr', 'a', 'route', 'link'}, 'kubectl': {'get', 'describe'},
}
V_RE = re.compile(
    r'(?:^|[\s/;&|(`])(?:pytest|py\.test|unittest|nosetests|ctest|phpunit|jest|mocha|rspec|tox|'
    r'cargo\s+test|go\s+test|npm\s+(?:run\s+)?test|yarn\s+test|make\s+(?:test|check)|mvn\s+(?:test|verify)|'
    r'gradle\s+test|dotnet\s+test|diff|cmp|getfacl|ldd|md5sum|sha256sum|sha1sum|shellcheck)\b'
    r'|\btests?\b|\btest_\w+|_test\.|\.test\.|\bassert\b|\bverify\w*\b|\bvalidat\w*\b'
    r'|curl\s+(?:-\S+\s+)*(?:https?://)?(?:localhost|127\.0\.0\.1|0\.0\.0\.0)'
    r'|wget\s+(?:-\S+\s+)*(?:https?://)?(?:localhost|127\.0\.0\.1)'
    r'|python3?\s+-c\s+["\']\s*import\b|nc\s+-z|ss\s+-\w*l|netstat\s+-\w*l',
    re.I)
HEREDOC_RE = re.compile(r'<<-?\s*["\']?\w+["\']?')
EDITOR_RE = re.compile(r'(?:^|[\s;&|])(?:vim?|nvim|nano|emacs|ed|pico)\s+\S')
SED_I_RE = re.compile(r'(?:^|[\s;&|])sed\s+(?:-\S+\s+)*-[a-zA-Z]*i')
PERL_I_RE = re.compile(r'(?:^|[\s;&|])perl\s+(?:-\S+\s+)*-[a-zA-Z]*i')
TEE_RE = re.compile(r'(?:^|[\s;&|])tee\s+(?!/dev/)')
PY_WRITE_RE = re.compile(r'open\([^)]*["\'][wa]\+?["\']|\.write\(|\.to_csv\(|\.save\(|\.write_text\(|\.dump\(|savefig\(|np\.save|torch\.save', re.I)
REDIR_STRIP_RE = re.compile(r'(?:\d?>&\d|\d?>\s*/dev/null|&>\s*/dev/null|&>>?\s*\S+|\d>\s*/dev/null|2>\s*\S+)')
REDIR_RE = re.compile(r'(?<![<\d&])>{1,2}\s*(?!&)\S')
ENV_ASSIGN_RE = re.compile(r'^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+')
PREFIX_WORDS = {'sudo', 'time', 'nohup', 'exec', 'command', 'builtin', 'nice', 'stdbuf', 'env', 'xargs', 'bash', 'sh', 'zsh', 'timeout'}
SPLIT_RE = re.compile(r'\s*(?:&&|\|\||;|\||\n)\s*')


def _first_token_info(sub):
    sub = sub.strip()
    sub = ENV_ASSIGN_RE.sub('', sub)
    toks = sub.split()
    # drop wrappers like sudo / timeout 30 / time
    while toks and os.path.basename(toks[0]) in PREFIX_WORDS:
        w = os.path.basename(toks.pop(0))
        if w == 'timeout' and toks and re.match(r'^-?[\d.]+[smhd]?$', toks[0]):
            toks.pop(0)
        if w in ('bash', 'sh', 'zsh') and toks and toks[0] == '-c':
            toks.pop(0)
            if toks:
                toks[0] = toks[0].strip('\'"')
        if w == 'env' and toks and '=' in toks[0]:
            toks.pop(0)
    if not toks:
        return '', []
    return os.path.basename(toks[0]), toks[1:]

READ_ONLY_SED_RE = re.compile(r'^sed\s+(?:-[nEr]+\s+)*(?:-e\s+)?["\']?[^"\']*?p["\']?(?:\s+\S+)*$')
RUN_TOKENS = {'python', 'python3', 'python2', 'node', 'ruby', 'perl', 'php', 'java', 'javac', 'make', 'cmake', 'cargo', 'go',
              'gcc', 'g++', 'clang', 'clang++', 'rustc', 'npm', 'yarn', 'pytest', 'mvn', 'gradle', 'dotnet', 'julia', 'Rscript',
              'ghc', 'ocaml', 'opam', 'dune', 'swift', 'kotlin', 'scala', 'sbt', 'pip', 'pip3', 'conda', 'apt', 'apt-get', 'docker',
              'qemu-system-x86_64', 'ffmpeg', 'convert', 'pmars', 'tmux'}
ECHO_C_RE = re.compile(r'\btask\b[^\n]{0,40}\b(?:complete|completed|done|finished|accomplished)\b|completed successfully|'
                       r'summary of (?:completed|changes|work|implementation)|final (?:results?|summary)|all (?:tasks|requirements)\b[^\n]{0,30}\b(?:complete|met|satisfied|done)', re.I)


def _all_explore(body):
    """True iff every sub-command is read-only exploration (echo sub-commands are neutral)."""
    parts = [p for p in SPLIT_RE.split(body) if p.strip()]
    if not parts:
        return False
    seen_e = False
    for p in parts:
        if '--help' in p or '--version' in p or re.search(r'\s-h\b', p):
            seen_e = True
            continue
        first, rest = _first_token_info(p)
        if first in ('echo', 'printf', 'true', 'false', 'sleep'):
            continue
        if first in E_FIRST_TOKENS:
            seen_e = True
            continue
        if first in E_SUBCMD and rest and rest[0] in E_SUBCMD[first]:
            seen_e = True
            continue
        if first in ('python', 'python3') and rest[:1] == ['--version']:
            seen_e = True
            continue
        if first == 'sed' and not SED_I_RE.search(p) and (re.search(r'\s-n\b', p) or re.search(r'p[\'"]?\s*$|p[\'"]?\s+\S+$', p)):
            seen_e = True
            continue
        if first in ('sqlite3', 'psql', 'mysql') and re.search(r'\b(?:select|\.schema|\.tables|\.indexes|pragma|show|describe|\\d)\b', p, re.I) and not re.search(r'\b(?:insert|update|delete|create|drop|alter)\b', p, re.I):
            seen_e = True
            continue
        return False
    return seen_e


def _all_echo(body):
    parts = [p for p in SPLIT_RE.split(body) if p.strip()]
    return bool(parts) and all(_first_token_info(p)[0] in ('echo', 'printf') for p in parts)


def _redirect_is_write(body):
    """A `>`/`>>` redirect counts as W unless the redirected sub-command is a program run
    (python script.py > log, make > build.log ...), which stays X."""
    stripped = REDIR_STRIP_RE.sub('', body)
    for p in SPLIT_RE.split(stripped):
        if REDIR_RE.search(p):
            first, _ = _first_token_info(p.split('>')[0])
            if first in RUN_TOKENS or first.startswith('./') or p.strip().startswith('./'):
                continue
            return True
    return False


def _ipython_cell_body(cmd):
    m = re.search(r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"', cmd)
    return _json_unescape(m.group(1)) if m else cmd


def classify_step(step, scaffold):
    """Return one of E V W X C P (R and O are never emitted: they need semantics)."""
    cmd = step['command']
    # --- C: completion claim ----------------------------------------------------
    if scaffold == 'openhands' and cmd.startswith('TOOL_CALL finish'):
        return 'C'
    if scaffold == 'miniswe' and 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' in cmd:
        return 'C'
    if scaffold == 'terminus2' and step['task_complete']:
        return 'C'
    if cmd and _all_echo(cmd) and ECHO_C_RE.search(cmd):
        return 'C'
    # --- P: no command, analysis only -------------------------------------------
    if not cmd:
        if scaffold == 'terminus2' and step.get('keystroke_sent'):
            return 'X'   # Enter / C-c / wait keystroke was sent (screen changed or marker present)
        return 'P'
    if scaffold == 'openhands' and (cmd.startswith('TOOL think') or cmd.startswith('TOOL_CALL task_tracker')):
        return 'P'
    body = cmd
    is_py = False
    if scaffold == 'openhands':
        if cmd.startswith('TOOL_CALL execute_ipython_cell'):
            body = _ipython_cell_body(cmd)
            is_py = True
        elif cmd.startswith('[ipython]'):
            body = cmd[len('[ipython]'):]
            is_py = True
        elif re.match(r'^EDITOR_(STR_REPLACE|CREATE|INSERT|UNDO_EDIT)', cmd) or re.match(r'^\[edit\b', cmd):
            return 'W'
        elif re.match(r'^\[read\]', cmd) or re.match(r'^\[str_replace_editor [^\]]*\]\s*view', cmd) or re.match(r'^EDITOR_VIEW|^TOOL_CALL str_replace_editor\(\{"command": "view"', cmd):
            return 'E'
        elif re.match(r'^\[str_replace_editor', cmd):
            return 'W'
        elif cmd.startswith('execute_bash(<missing command>)'):
            return 'X'   # command text lost in the export; a bash command was executed
    # --- W (strong forms): heredoc into cat/tee/redirect, sed -i, editors ---------
    if HEREDOC_RE.search(body):
        head = body.split('<<', 1)[0]
        first, _ = _first_token_info(head.split('\n')[0])
        if first in ('cat', 'tee') or REDIR_RE.search(REDIR_STRIP_RE.sub('', head)) or re.search(r'\b(?:python3?|node|ruby|perl|php|bash|sh|sqlite3|psql|mysql|ocaml|julia|Rscript)\b', head) is None:
            return 'W'
        if PY_WRITE_RE.search(body):
            return 'W'
    if SED_I_RE.search(body) or PERL_I_RE.search(body) or EDITOR_RE.search(body) or TEE_RE.search(body):
        return 'W'
    if is_py and PY_WRITE_RE.search(body):
        return 'W'
    # --- V ----------------------------------------------------------------------
    if V_RE.search(body):
        return 'V'
    if is_py and re.search(r'\bassert\b|\btest', body, re.I):
        return 'V'
    # --- W (redirect of content, not of a program run) ----------------------------
    if not is_py and _redirect_is_write(body):
        return 'W'
    if is_py and re.search(r'^\s*(?:import|from)\s', body, re.M) and len(body.strip().splitlines()) <= 3 and not re.search(r'\(', body):
        return 'V'  # bare import check
    # --- E ----------------------------------------------------------------------
    if not is_py and _all_explore(body):
        return 'E'
    return 'X'


def human_step_codes(rec):
    """Expand action_segments into {step: code}."""
    codes = {}
    for a, b, c in rec.get('action_segments') or []:
        for i in range(int(a), int(b) + 1):
            codes[i] = c
    return codes


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def write_json(path, obj):
    with open(path, 'w') as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
