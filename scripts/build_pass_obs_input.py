#!/usr/bin/env python3
"""Build structured input for the PASS first_error observable/silent labeling.
Zero LLM. For each PASS with >=1 error event, collect: case_id, first_error_step,
first_error_evidence, and the command+terminal_output of steps [first_error-1 .. +1].
Writes pass_obs_input.json."""
import json, os

recs = [r for r in json.load(open('data/traj_data_v2_all89tasks.json')) if r.get('schema_version') == 'v2']
pas = [r for r in recs if 't_commit' not in r]
pe = [r for r in pas if r.get('num_error_events', 0) >= 1 and r.get('first_error_evidence') and r.get('first_error_step')]

def clip(s, n):
    s = (s or '').strip().replace('\r', '')
    return s[:n] + (' …' if len(s) > n else '')

def step_text(traj, n):
    f = f"{traj}/step_{n}.jsonl"
    if not os.path.exists(f): return None
    o = json.load(open(f))
    cmd = clip(o.get('command'), 160)
    out = clip(o.get('terminal_result'), 380)
    return f"  step {n}  $ {cmd}\n            {out}"

out = []
missing = 0
for r in pe:
    parts = r['case_id'].split('__')
    traj = f"merged_trajectories/{parts[0]}/{parts[1]}/{parts[2]}"
    fe = r['first_error_step']
    ctx_lines = []
    for n in (fe - 1, fe, fe + 1):
        if n >= 1:
            t = step_text(traj, n)
            if t: ctx_lines.append(t)
    if not ctx_lines:
        missing += 1
    out.append({
        'case_id': r['case_id'],
        'first_error_step': fe,
        'first_error_evidence': r['first_error_evidence'],
        'context': '\n'.join(ctx_lines) if ctx_lines else '(no step files found)',
    })

json.dump(out, open('data/pass_obs_input.json', 'w'), indent=2, ensure_ascii=False)
print(f"wrote pass_obs_input.json: {len(out)} cases  ({missing} with no readable context)")
print("\n===== 4 SAMPLES (what each labeler item looks like) =====")
import re
OBS = re.compile(r'error|fail|not found|traceback|exit code|denied|already exists|404|forbidden', re.I)
shown = {'obs': 0, 'sil': 0}
for it in out:
    kind = 'obs' if OBS.search(it['first_error_evidence']) else 'sil'
    if shown[kind] >= 2: continue
    shown[kind] += 1
    print(f"\n--- {it['case_id']}  (first_error_step={it['first_error_step']}) ---")
    print(f"evidence: {it['first_error_evidence'][:160]}")
    print(it['context'][:520])
    if sum(shown.values()) >= 4: break
