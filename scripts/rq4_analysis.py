#!/usr/bin/env python3
"""RQ4 (Recovery) analysis — recovered errors (PASS) vs decisive errors (FAIL).
Uses ONLY existing v2 fields. Outputs results/results_rq4.json + prints a summary.

Three things, all on existing data:
  Q2  what the agent does in the K steps AFTER a signal (anchored on the signal,
      not on the outcome -> avoids survivorship bias) + bootstrap CI + chi2 p
  ROB robustness over FAIL anchor (forewarning / t_surface) x K (2/3/5)
  Q3  (a) verification discipline with EQUALIZED anchor (the 72-pt gap was mostly
          anchor mismatch: claim vs lock), (b) correction window, (c) recognition
"""
import json, statistics as st
import numpy as np
from collections import Counter
try:
    from scipy.stats import chi2_contingency, mannwhitneyu
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

rng = np.random.default_rng(42)
recs = [r for r in json.load(open('data/traj_data_v2_all89tasks.json')) if r.get('schema_version') == 'v2']
fail = [r for r in recs if 't_commit' in r]
pas  = [r for r in recs if 't_commit' not in r]

def expand(r):
    arr = ['O'] * r['m']
    for s, e, c in r['action_segments']:
        for i in range(s, e + 1):
            if 1 <= i <= r['m']: arr[i - 1] = c
    return arr

def window_after(r, anchor, K):
    """action codes in the K steps strictly after step `anchor` (1-indexed)."""
    if not anchor or anchor < 1 or anchor >= r['m']: return None
    return expand(r)[anchor:min(anchor + K, r['m'])]

def boot_diff(a, b, n=10000):
    a = np.asarray(a, float); b = np.asarray(b, float)
    obs = a.mean() - b.mean()
    da = rng.choice(a, (n, len(a))).mean(1)
    db = rng.choice(b, (n, len(b))).mean(1)
    d = da - db
    return float(obs), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))

def chi2_p(a, b):
    if not HAVE_SCIPY: return None
    ta = [sum(a), len(a) - sum(a)]; tb = [sum(b), len(b) - sum(b)]
    try: return float(chi2_contingency([ta, tb])[1])
    except Exception: return None

out = {}

# ---------- baseline ----------
out['baseline'] = {
    'n_fail': len(fail), 'n_pass': len(pas),
    'pass_with_error': sum(r.get('num_error_events', 0) >= 1 for r in pas) / len(pas),
}

# ---------- Q2: verify within K after the first signal ----------
def verify_after_set(anchor_pass, anchor_fail, K):
    pv, fv = [], []
    for r in pas:
        w = window_after(r, r.get(anchor_pass), K)
        if w is not None: pv.append(int('V' in w))
    for r in fail:
        w = window_after(r, r.get(anchor_fail), K)
        if w is not None: fv.append(int('V' in w))
    return pv, fv

pv, fv = verify_after_set('first_error_step', 'forewarning_first_step', 3)
obs, lo, hi = boot_diff(pv, fv)
out['Q2_verify_after_3'] = {'pass_rate': sum(pv)/len(pv), 'fail_rate': sum(fv)/len(fv),
                            'pass_n': len(pv), 'fail_n': len(fv),
                            'diff': obs, 'ci': [lo, hi], 'p_chi2': chi2_p(pv, fv)}

# verify+recover SHARE of those K steps, per trajectory
def vr_share_set(anchor_pass, anchor_fail, K):
    pvr, fvr = [], []
    for r in pas:
        w = window_after(r, r.get(anchor_pass), K)
        if w: pvr.append(sum(c in 'VR' for c in w) / len(w))
    for r in fail:
        w = window_after(r, r.get(anchor_fail), K)
        if w: fvr.append(sum(c in 'VR' for c in w) / len(w))
    return pvr, fvr

pvr, fvr = vr_share_set('first_error_step', 'forewarning_first_step', 3)
obs2, lo2, hi2 = boot_diff(pvr, fvr)
p_mw = float(mannwhitneyu(pvr, fvr).pvalue) if HAVE_SCIPY else None
out['Q2_VR_share_after_3'] = {'pass_mean': float(np.mean(pvr)), 'fail_mean': float(np.mean(fvr)),
                              'diff': obs2, 'ci': [lo2, hi2], 'p_mw': p_mw}

print("=" * 68)
print("Q2  reaction in the 3 steps AFTER the first signal (anchored on signal)")
print("=" * 68)
m = out['Q2_verify_after_3']
p_chi = f"{m['p_chi2']:.1e}" if m['p_chi2'] is not None else "n/a (install scipy)"
print(f"  verify within 3 steps:  PASS {m['pass_rate']*100:.0f}% (n={m['pass_n']})  vs  "
      f"FAIL {m['fail_rate']*100:.0f}% (n={m['fail_n']})")
print(f"     diff +{m['diff']*100:.1f} pts   95% CI [{m['ci'][0]*100:+.1f}, {m['ci'][1]*100:+.1f}]   "
      f"p={p_chi}")
v = out['Q2_VR_share_after_3']
p_mw_str = f"{v['p_mw']:.1e}" if v['p_mw'] is not None else "n/a (install scipy)"
print(f"  verify+recover share:   PASS {v['pass_mean']*100:.1f}%  vs  FAIL {v['fail_mean']*100:.1f}%   "
      f"diff +{v['diff']*100:.1f} pts  CI [{v['ci'][0]*100:+.1f},{v['ci'][1]*100:+.1f}]  p={p_mw_str}")

# ---------- Robustness ----------
print("\n" + "=" * 68)
print("ROBUSTNESS  verify-after-rate gap (PASS − FAIL, pts)")
print(f"  {'FAIL anchor':16}{'K=2':>10}{'K=3':>10}{'K=5':>10}")
rob = {}
for af, lbl in [('forewarning_first_step', 'forewarning'), ('t_surface', 't_surface')]:
    row = []
    for K in [2, 3, 5]:
        a, b = verify_after_set('first_error_step', af, K)
        d, l, h = boot_diff(a, b)
        row.append(d * 100); rob[f'{lbl}_K{K}'] = {'diff': d, 'ci': [l, h]}
    print(f"  {lbl:16}" + "".join(f"{x:>+10.1f}" for x in row))
out['robustness'] = rob

# ---------- Q3(a): verification discipline, equalized anchor ----------
def claim_hygiene(r, K=3):
    """is there a V in the K steps before the LAST completion claim (C)?"""
    arr = expand(r); cs = [i for i, c in enumerate(arr) if c == 'C']
    if not cs: return None
    last = cs[-1]
    return int('V' in arr[max(0, last - K):last])

pch = [v for r in pas if (v := claim_hygiene(r)) is not None]
fch = [v for r in fail if (v := claim_hygiene(r)) is not None]
obs3, lo3, hi3 = boot_diff(pch, fch)
pvb = sum(r.get('verification_before_claim', False) for r in pas) / len(pas)
fvb = len([r for r in fail if r.get('verification_ever') and r.get('first_relevant_verification_step')
           and r['first_relevant_verification_step'] <= r['t_commit']]) / len(fail)
out['Q3a_verification'] = {
    'nonequalized': {'pass_before_claim': pvb, 'fail_before_lock': fvb, 'gap': pvb - fvb},
    'equalized_claim_hygiene': {'pass_rate': sum(pch)/len(pch), 'fail_rate': sum(fch)/len(fch),
                                'diff': obs3, 'ci': [lo3, hi3], 'p_chi2': chi2_p(pch, fch),
                                'pass_n': len(pch), 'fail_n': len(fch)},
}
print("\n" + "=" * 68)
print("Q3(a)  VERIFICATION DISCIPLINE — the anchor was doing most of the work")
print("=" * 68)
print(f"  non-equalized (PASS before-claim vs FAIL before-LOCK):  "
      f"{pvb*100:.0f}% vs {fvb*100:.0f}%   gap {(pvb-fvb)*100:.0f} pts")
print(f"  EQUALIZED (both: V in 3 steps before final claim):      "
      f"{sum(pch)/len(pch)*100:.0f}% vs {sum(fch)/len(fch)*100:.0f}%   "
      f"gap {obs3*100:.0f} pts  CI [{lo3*100:+.0f},{hi3*100:+.0f}]")
print("  --> most of the 72-pt headline gap was anchor mismatch (claim vs lock), not verification itself")

# ---------- Q3(b) window, Q3(c) recognition ----------
det = sorted(r.get('max_detour_length', 0) for r in pas if r.get('num_error_events', 0) >= 1)
fw  = sorted(r['t_commit'] - r['t_err'] for r in fail)
qf = lambda xs, p: xs[int(len(xs) * p)]
out['Q3b_window'] = {
    'pass_detour': {'median': st.median(det), 'p75': qf(det, .75), 'p90': qf(det, .90)},
    'fail_fixwin': {'median': st.median(fw), 'eq0': sum(x == 0 for x in fw)/len(fw), 'ge3': sum(x >= 3 for x in fw)/len(fw)},
}
out['Q3c_recognition'] = {'fail_never_aware': sum(r['awareness'] == 'never_aware' for r in fail)/len(fail)}
print("\n" + "=" * 68)
print("Q3(b) correction window  |  Q3(c) recognition")
print("=" * 68)
print(f"  PASS detour: median {st.median(det)}, p90 {qf(det,.90)}   |   "
      f"FAIL fix_win: median {st.median(fw)}, ==0 {sum(x==0 for x in fw)/len(fw)*100:.0f}%, >=3 {sum(x>=3 for x in fw)/len(fw)*100:.0f}%")
print(f"  FAIL never noticed decisive error: {sum(r['awareness']=='never_aware' for r in fail)/len(fail)*100:.0f}%  "
      f"(survivorship caveat: PASS ~100% by construction)")

import os; os.makedirs('results', exist_ok=True)
json.dump(out, open('results/results_rq4.json', 'w'), indent=2)
print("\nwrote results/results_rq4.json")
