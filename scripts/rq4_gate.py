#!/usr/bin/env python3
"""RQ4 reframed as a TWO-STAGE GATE (observability -> response), symmetric by design.
  Stage 1  observability: does the error announce itself?
           FAIL: derived (forewarning OR t_surface<=t_commit).  PASS: rule preview on evidence.
  Stage 2  response: in the self-revealing subset, stop-and-check vs plow-ahead (action_segments).
  Stage 3  response latency (symmetric): signal -> first verify/recover; FAIL censored at lock-in.
Existing fields only. PASS observability is a RULE PREVIEW pending one LLM labeling pass."""
import json, re, statistics as st
import numpy as np
from collections import Counter
try:
    from scipy.stats import chi2_contingency; HS = True
except Exception:
    HS = False
rng = np.random.default_rng(42)
recs = [r for r in json.load(open('data/traj_data_v2_all89tasks.json')) if r.get('schema_version') == 'v2']
fail = [r for r in recs if 't_commit' in r]; pas = [r for r in recs if 't_commit' not in r]

def expand(r):
    a = ['O'] * r['m']
    for s, e, c in r['action_segments']:
        for i in range(s, e + 1):
            if 1 <= i <= r['m']: a[i - 1] = c
    return a
def boot_diff(a, b, n=10000):
    a = np.asarray(a, float); b = np.asarray(b, float); obs = a.mean() - b.mean()
    d = rng.choice(a, (n, len(a))).mean(1) - rng.choice(b, (n, len(b))).mean(1)
    return float(obs), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
def chi2p(a, b):
    if not HS: return None
    try: return float(chi2_contingency([[sum(a), len(a) - sum(a)], [sum(b), len(b) - sum(b)]])[1])
    except Exception: return None

out = {}
# ---------------- STAGE 1: observability gate ----------------
print("=" * 70); print("STAGE 1 — OBSERVABILITY: does the error announce itself?"); print("=" * 70)
def revealing(r): return bool(r.get('forewarning_present')) or (r.get('t_surface') and r['t_surface'] <= r['t_commit'])
f_rev = [r for r in fail if revealing(r)]; f_sil = [r for r in fail if not revealing(r)]
pe = [r for r in pas if r.get('num_error_events', 0) >= 1 and r.get('first_error_evidence')]
lab = json.load(open('data/pass_error_observability.json'))   # LLM-confirmed observable/silent
p_obs = [r for r in pe if lab.get(r['case_id'], {}).get('label') == 'observable']
p_sil = [r for r in pe if lab.get(r['case_id'], {}).get('label') == 'silent']
print(f"  FAIL decisive error : self-revealing {len(f_rev)/len(fail)*100:.0f}%  |  SILENT {len(f_sil)/len(fail)*100:.0f}%")
print(f"  PASS first error    : observable {len(p_obs)/len(pe)*100:.0f}%  |  SILENT {len(p_sil)/len(pe)*100:.0f}%  (LLM-confirmed, n={len(pe)})")
print(f"  >> observability is SIMILAR on both sides ({len(p_obs)/len(pe)*100:.0f}% vs {len(f_rev)/len(fail)*100:.0f}% have a signal)")
print(f"     -> observability is a GATE (32% of fatal errors are silent = no chance) but NOT the main discriminator")
out['stage1'] = {'fail_silent': len(f_sil)/len(fail), 'fail_revealing': len(f_rev)/len(fail),
                 'pass_observable': len(p_obs)/len(pe), 'pass_silent': len(p_sil)/len(pe), 'pass_n': len(pe)}

# ---------------- STAGE 2: response mode (self-revealing subset) ----------------
print("\n" + "=" * 70); print("STAGE 2 — RESPONSE: in the SELF-REVEALING subset, what does it do?"); print("=" * 70)
K = 3
def window(r, anc, K):
    if not anc or anc < 1 or anc >= r['m']: return None
    return expand(r)[anc:min(anc + K, r['m'])]
def mode(w):
    if w is None: return None
    if any(c in 'VR' for c in w): return 'stop_and_check'
    if any(c in 'WX' for c in w): return 'plow_ahead'
    return 'other'
p_modes = [m for r in p_obs if (m := mode(window(r, r.get('first_error_step'), K)))]
f_modes = [m for r in fail if revealing(r) and r.get('forewarning_first_step')
           and (m := mode(window(r, r['forewarning_first_step'], K)))]
def dist(ms):
    c = Counter(ms); t = len(ms); return {k: c[k]/t*100 for k in ['stop_and_check', 'plow_ahead', 'other']}, t
pd, pn = dist(p_modes); fd, fn = dist(f_modes)
print(f"  response mode in {K} steps after signal   (PASS n={pn}, FAIL n={fn})")
print(f"  {'mode':18}{'PASS%':>8}{'FAIL%':>8}{'Δ':>8}")
for m in ['stop_and_check', 'plow_ahead', 'other']:
    print(f"  {m:18}{pd[m]:8.1f}{fd[m]:8.1f}{pd[m]-fd[m]:>+8.1f}")
ps = [int(m == 'stop_and_check') for m in p_modes]; fs = [int(m == 'stop_and_check') for m in f_modes]
o, l, h = boot_diff(ps, fs)
p = chi2p(ps, fs); p_str = f"{p:.1e}" if p is not None else "n/a (install scipy)"
print(f"  >> stop-and-check: PASS {sum(ps)/len(ps)*100:.0f}% vs FAIL {sum(fs)/len(fs)*100:.0f}%  "
      f"diff +{o*100:.1f} CI[{l*100:+.1f},{h*100:+.1f}] p={p_str}")
out['stage2'] = {'pass': pd, 'fail': fd, 'stop_check_diff': o, 'ci': [l, h], 'pass_n': pn, 'fail_n': fn}

# ---------------- STAGE 3: symmetric response latency ----------------
print("\n" + "=" * 70); print("STAGE 3 — RESPONSE LATENCY (symmetric): signal -> first verify/recover"); print("=" * 70)
def first_vr(r, anc, cap):
    arr = expand(r)
    for i in range(anc, min(cap, r['m'])):
        if arr[i] in 'VR': return i + 1 - anc
    return None
p_lat, p_cens = [], 0
for r in p_obs:
    a = r.get('first_error_step')
    if a and a < r['m']:
        L = first_vr(r, a, r['m'])
        (p_lat.append(L) if L is not None else None) if L is not None else 0
        if L is None: p_cens += 1
f_lat, f_cens = [], 0
for r in fail:
    if revealing(r) and r.get('forewarning_first_step') and r['forewarning_first_step'] < r['m']:
        L = first_vr(r, r['forewarning_first_step'], r['t_commit'])
        if L is None: f_cens += 1
        else: f_lat.append(L)
pc = p_cens/(p_cens+len(p_lat))*100; fc = f_cens/(f_cens+len(f_lat))*100
print(f"  PASS: median latency {st.median(p_lat)} steps  |  NEVER responded before end:  {pc:.0f}%")
print(f"  FAIL: median latency {st.median(f_lat)} steps  |  NEVER responded before LOCK: {fc:.0f}%")
print(f"  >> even WITH a signal, {fc:.0f}% of failing agents never verify/recover before locking in")
out['stage3'] = {'pass_median_latency': st.median(p_lat), 'fail_median_latency': st.median(f_lat),
                 'pass_censored': pc/100, 'fail_censored': fc/100}

import os; os.makedirs('results', exist_ok=True)
json.dump(out, open('results/results_rq4_gate.json', 'w'), indent=2)
print("\nwrote results/results_rq4_gate.json")
