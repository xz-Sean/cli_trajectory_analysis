"""E1.4 -- command-level action classifier vs human action_segments.

Classifier (e1_common.classify_step), priority order:
  C : scaffold completion marker (openhands TOOL_CALL finish, miniswe
      COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT, terminus2 task_complete=true)
  P : no command (think/wait step), openhands TOOL think / task_tracker
  W : EDITOR_* tool; heredoc into cat/tee/redirect; sed -i / perl -i; vi/nano/...;
      tee; python code that writes files; (after V) any remaining `>`/`>>` redirect
  V : pytest/unittest/... ; the word test(s)/test_* ; diff/cmp/getfacl/ldd/checksums;
      assert / verify* / validat* ; curl|wget localhost ; python -c "import ..."
  E : every sub-command (split on && || ; | newline) starts with an explore token
      (ls cat head tail find grep which pwd tree stat file wc ... , git status/log/...,
      pip list/show, --help/--version)
  X : everything else
R and O are never emitted (need semantics) and are excluded from accuracy; they
appear as rows of the confusion matrix for completeness.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_common as C  # noqa: E402

CODES = ['E', 'V', 'W', 'X', 'C', 'P']
ALL = CODES + ['R', 'O']


def main():
    ann = C.load_annotations()
    per_traj = []
    conf = collections.Counter()
    conf_by = {'scaffold': collections.defaultdict(collections.Counter), 'model': collections.defaultdict(collections.Counter), 'kind': collections.defaultdict(collections.Counter)}
    examples = collections.defaultdict(list)
    seg_tot, seg_ok, seg_any = collections.Counter(), collections.Counter(), collections.Counter()
    seg_tot_by, seg_ok_by = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for rec in ann:
        cid = rec['case_id']
        task, sc, mo = C.split_case(cid)
        kind = 'FAIL' if C.is_fail(rec) else 'PASS'
        steps, missing = C.load_traj(cid)
        human = C.human_step_codes(rec)
        n = agree = evaln = 0
        auto_codes = {}
        for st in steps:
            h = human.get(st['i'])
            if h is None:
                continue
            a = C.classify_step(st, sc)
            auto_codes[st['i']] = a
            conf[(h, a)] += 1
            conf_by['scaffold'][sc][(h, a)] += 1
            conf_by['model'][mo][(h, a)] += 1
            conf_by['kind'][kind][(h, a)] += 1
            n += 1
            if h in CODES:
                evaln += 1
                if h == a:
                    agree += 1
                elif len(examples[(h, a)]) < 5:
                    examples[(h, a)].append({'case_id': cid, 'step': st['i'], 'command': st['command'][:160]})
        # segment-level: does the majority auto code of a human segment equal the human code?
        for a0, b0, c0 in rec.get('action_segments') or []:
            if c0 not in CODES:
                continue
            votes = collections.Counter(auto_codes[i] for i in range(int(a0), int(b0) + 1) if i in auto_codes)
            if not votes:
                continue
            maj = votes.most_common(1)[0][0]
            seg_tot[c0] += 1
            seg_tot_by[sc][c0] += 1
            if maj == c0:
                seg_ok[c0] += 1
                seg_ok_by[sc][c0] += 1
            if c0 in votes:
                seg_any[c0] += 1
        per_traj.append({'case_id': cid, 'scaffold': sc, 'model': mo, 'kind': kind, 'n_steps': n, 'n_eval': evaln, 'agree': agree,
                         'acc_pct': C.pct(agree, evaln), 'auto_codes': ''.join(auto_codes.get(i, '?') for i in range(1, len(steps) + 1)),
                         'human_codes': ''.join(human.get(i, '?') for i in range(1, len(steps) + 1)), 'missing_steps': missing})

    def metrics(cnt):
        tot = sum(v for (h, a), v in cnt.items() if h in CODES)
        agree = sum(v for (h, a), v in cnt.items() if h in CODES and h == a)
        per = {}
        for c in CODES:
            tp = cnt[(c, c)]
            hum = sum(v for (h, a), v in cnt.items() if h == c)
            aut = sum(v for (h, a), v in cnt.items() if a == c and h in CODES)
            per[c] = {'human_n': hum, 'auto_n': aut, 'recall_pct': C.pct(tp, hum), 'precision_pct': C.pct(tp, aut),
                      'f1': round(2 * tp / (hum + aut), 3) if hum + aut else None}
        matrix = {h: {a: cnt[(h, a)] for a in CODES} for h in ALL}
        return {'n_eval_steps': tot, 'n_all_steps': sum(cnt.values()), 'accuracy_pct': C.pct(agree, tot), 'per_code': per, 'confusion_human_rows_x_auto_cols': matrix}

    summary = {'overall': metrics(conf),
               'by_scaffold': {sc: metrics(conf_by['scaffold'][sc]) for sc in C.SCAFFOLDS},
               'by_model': {mo: metrics(conf_by['model'][mo]) for mo in C.MODELS},
               'by_kind': {k: metrics(conf_by['kind'][k]) for k in ('FAIL', 'PASS')},
               'segment_level': {
                   'note': 'human action_segments are runs; a run is counted correct if the MAJORITY auto code over its steps equals the human code; any_pct = human code appears at least once in the run',
                   'overall_majority_pct': C.pct(sum(seg_ok.values()), sum(seg_tot.values())),
                   'overall_any_pct': C.pct(sum(seg_any.values()), sum(seg_tot.values())),
                   'n_segments': sum(seg_tot.values()),
                   'per_code_majority_pct': {c: C.pct(seg_ok[c], seg_tot[c]) for c in CODES},
                   'per_code_any_pct': {c: C.pct(seg_any[c], seg_tot[c]) for c in CODES},
                   'by_scaffold_majority_pct': {sc: C.pct(sum(seg_ok_by[sc].values()), sum(seg_tot_by[sc].values())) for sc in C.SCAFFOLDS}},
               'disagreement_examples': {'%s->%s' % k: v for k, v in examples.items()},
               'rules': __doc__}
    C.write_json(os.path.join(C.OUT_DIR, 'segments_auto.json'), {'summary': summary, 'per_trajectory': per_traj})
    o = summary['overall']
    print('accuracy', o['accuracy_pct'], 'n', o['n_eval_steps'])
    print('      ' + ' '.join('%6s' % a for a in CODES))
    for h in ALL:
        print('%5s ' % h + ' '.join('%6d' % o['confusion_human_rows_x_auto_cols'][h][a] for a in CODES))
    for c in CODES:
        print(c, o['per_code'][c])
    for sc in C.SCAFFOLDS:
        print(sc, summary['by_scaffold'][sc]['accuracy_pct'])
    for mo in C.MODELS:
        print(mo, summary['by_model'][mo]['accuracy_pct'])


if __name__ == '__main__':
    main()
