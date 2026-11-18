"""E1.1 -- automatic t_surface detector (rule-based) vs human t_surface.

Rule set (applied to the *terminal output* of each step, in priority order;
t_surface_auto = earliest step where ANY strong tier fires):
  tier 1 test-failure     : FAILED | AssertionError | Error: .* test | <n> failed | tests? failed
  tier 2 process-level    : Traceback | Segmentation fault | core dumped
  tier 3 shell-level (ci) : command not found | No such file | Permission denied |
                            not a git repository | fatal: | error:
  weak  (separate field)  : empty output AND step classified W or X by the E1.4 classifier
Extension (reported separately as t_surface_auto_ext): tier 3b = non-zero exit code
  (miniswe <returncode>, openhands "executed with exit code N"); terminus2 has no exit codes.

Human t_surface is the earliest observable failure signal *relevant to the failure*;
the automatic rule has no notion of relevance, so we also report
t_surface_auto_ge_terr = earliest strong signal at step >= t_err.
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_common as C  # noqa: E402

RULES = [
    ('tier1_test', re.compile(r'\bFAILED\b|AssertionError|Error:.*\btests?\b|\b[1-9]\d* failed\b|\btests? failed\b')),
    ('tier2_process', re.compile(r'Traceback \(most recent call last\)|\bTraceback\b|Segmentation fault|core dumped')),
    ('tier3_shell', re.compile(r'command not found|No such file|Permission denied|not a git repository|fatal:|error:', re.I)),
]
RULE_DOC = {name: rx.pattern + ('  [case-insensitive]' if rx.flags & re.I else '') for name, rx in RULES}


def detect(steps, scaffold):
    """Return per-step signal list: (step, tier, snippet)."""
    strong, weak, ext = [], [], []
    for st in steps:
        out = st['output']
        hit = None
        for name, rx in RULES:
            m = rx.search(out)
            if m:
                s = max(0, m.start() - 40)
                hit = (name, out[s:m.end() + 60].replace('\n', ' '))
                break
        if hit:
            strong.append((st['i'], hit[0], hit[1]))
        elif st['exit_code'] not in (None, 0):
            ext.append((st['i'], 'tier3b_exit', 'exit code %s' % st['exit_code']))
        if not out.strip() and st['command']:
            code = C.classify_step(st, scaffold)
            if code in ('W', 'X'):
                weak.append((st['i'], 'weak_empty_' + code, ''))
    return strong, weak, ext


def main():
    ann = C.load_annotations()
    fails = [r for r in ann if C.is_fail(r)]
    rows = []
    log = []
    for rec in fails:
        cid = rec['case_id']
        task, sc, mo = C.split_case(cid)
        steps, missing = C.load_traj(cid)
        if missing:
            log.append({'case_id': cid, 'missing_steps': missing})
        strong, weak, ext = detect(steps, sc)
        t_err, t_commit, t_h = rec['t_err'], rec['t_commit'], rec.get('t_surface')
        t_auto = strong[0][0] if strong else None
        t_weak = weak[0][0] if weak else None
        allext = sorted(strong + ext)
        t_ext = allext[0][0] if allext else None
        ge = [s for s in strong if s[0] >= t_err]
        t_auto_ge = ge[0][0] if ge else None
        rows.append({
            'case_id': cid, 'scaffold': sc, 'model': mo, 'm': rec['m'],
            't_err': t_err, 't_commit': t_commit, 't_surface_human': t_h,
            't_surface_auto': t_auto, 't_surface_auto_tier': strong[0][1] if strong else None,
            't_surface_auto_snippet': strong[0][2] if strong else None,
            't_surface_auto_ge_terr': t_auto_ge,
            't_surface_auto_ext': t_ext,
            't_surface_weak': t_weak,
            'n_strong_steps': len(strong),
            'human_evidence': rec.get('t_surface_evidence'),
            'strong_at_human_step': (t_h is not None and any(s[0] == t_h for s in strong)),
            'strong_within1_human_step': (t_h is not None and any(abs(s[0] - t_h) <= 1 for s in strong)),
        })

    def summarise(sub):
        n = len(sub)
        both = [r for r in sub if r['t_surface_human'] is not None and r['t_surface_auto'] is not None]
        both_ge = [r for r in sub if r['t_surface_human'] is not None and r['t_surface_auto_ge_terr'] is not None]
        d = lambda r, k: abs(r[k] - r['t_surface_human'])  # noqa: E731
        surf_auto = [r for r in sub if r['t_surface_auto'] is not None]
        surf_hum = [r for r in sub if r['t_surface_human'] is not None]
        surf_ext = [r for r in sub if r['t_surface_auto_ext'] is not None]
        return {
            'n': n,
            'human_silent_pct': C.pct(n - len(surf_hum), n),
            'auto_silent_pct': C.pct(n - len(surf_auto), n),
            'auto_ext_silent_pct': C.pct(n - len(surf_ext), n),
            'auto_silent_incl_weak_pct': C.pct(sum(1 for r in sub if r['t_surface_auto'] is None and r['t_surface_weak'] is None), n),
            'human_null_auto_nonnull': sum(1 for r in sub if r['t_surface_human'] is None and r['t_surface_auto'] is not None),
            'human_nonnull_auto_null': sum(1 for r in sub if r['t_surface_human'] is not None and r['t_surface_auto'] is None),
            'both_nonnull': len(both),
            'agree_exact_pct': C.pct(sum(1 for r in both if d(r, 't_surface_auto') == 0), len(both)),
            'agree_pm1_pct': C.pct(sum(1 for r in both if d(r, 't_surface_auto') <= 1), len(both)),
            'agree_pm3_pct': C.pct(sum(1 for r in both if d(r, 't_surface_auto') <= 3), len(both)),
            'auto_earlier_than_human_pct': C.pct(sum(1 for r in both if r['t_surface_auto'] < r['t_surface_human']), len(both)),
            'auto_later_than_human_pct': C.pct(sum(1 for r in both if r['t_surface_auto'] > r['t_surface_human']), len(both)),
            'median_abs_diff': _median([d(r, 't_surface_auto') for r in both]),
            'ge_terr_both_nonnull': len(both_ge),
            'ge_terr_agree_exact_pct': C.pct(sum(1 for r in both_ge if d(r, 't_surface_auto_ge_terr') == 0), len(both_ge)),
            'ge_terr_agree_pm1_pct': C.pct(sum(1 for r in both_ge if d(r, 't_surface_auto_ge_terr') <= 1), len(both_ge)),
            'ge_terr_agree_pm3_pct': C.pct(sum(1 for r in both_ge if d(r, 't_surface_auto_ge_terr') <= 3), len(both_ge)),
            'any_strong_signal_at_human_step_pct': C.pct(sum(1 for r in surf_hum if r['strong_at_human_step']), len(surf_hum)),
            'any_strong_signal_within1_human_step_pct': C.pct(sum(1 for r in surf_hum if r['strong_within1_human_step']), len(surf_hum)),
            'human_surface_before_commit_pct': C.pct(sum(1 for r in surf_hum if r['t_surface_human'] < r['t_commit']), len(surf_hum)),
            'auto_surface_before_commit_pct': C.pct(sum(1 for r in surf_auto if r['t_surface_auto'] < r['t_commit']), len(surf_auto)),
            'auto_ge_terr_surface_before_commit_pct': C.pct(sum(1 for r in sub if r['t_surface_auto_ge_terr'] is not None and r['t_surface_auto_ge_terr'] < r['t_commit']),
                                                           sum(1 for r in sub if r['t_surface_auto_ge_terr'] is not None)),
            'auto_surface_before_terr_pct': C.pct(sum(1 for r in surf_auto if r['t_surface_auto'] < r['t_err']), len(surf_auto)),
        }

    summary = {'overall': summarise(rows), 'by_scaffold': {}, 'by_model': {}, 'rules': RULE_DOC,
               'human_reference': {'silent_pct': 28.0, 'surface_before_commit_pct': 28.3}}
    for sc in C.SCAFFOLDS:
        summary['by_scaffold'][sc] = summarise([r for r in rows if r['scaffold'] == sc])
    for mo in C.MODELS:
        summary['by_model'][mo] = summarise([r for r in rows if r['model'] == mo])
    tier = collections.Counter(r['t_surface_auto_tier'] for r in rows if r['t_surface_auto'])
    summary['overall']['first_signal_tier_counts'] = dict(tier)
    summary['missing_step_log'] = log
    C.write_json(os.path.join(C.OUT_DIR, 'tsurface_auto.json'), {'summary': summary, 'rows': rows})
    print(json.dumps(summary['overall'], indent=1))
    for sc in C.SCAFFOLDS:
        s = summary['by_scaffold'][sc]
        print(sc, 'auto_silent', s['auto_silent_pct'], 'human_silent', s['human_silent_pct'], 'exact', s['agree_exact_pct'], 'pm1', s['agree_pm1_pct'], 'pm3', s['agree_pm3_pct'])
    for mo in C.MODELS:
        s = summary['by_model'][mo]
        print(mo, 'auto_silent', s['auto_silent_pct'], 'human_silent', s['human_silent_pct'], 'exact', s['agree_exact_pct'], 'pm1', s['agree_pm1_pct'], 'pm3', s['agree_pm3_pct'])


def _median(xs):
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


if __name__ == '__main__':
    main()
