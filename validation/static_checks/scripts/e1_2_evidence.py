"""E1.2 -- evidence-quote localisation rate.

For every *_evidence field we try to locate the quote in the cited step's
command + agent_analysis + terminal_result (raw fields, concatenated):
  exact : normalised quote is a substring of the normalised step text
  fuzzy : best sliding-window token-set Jaccard >= 0.8 (window = |quote tokens| and 1.5x)
  near  : exact-or-fuzzy in a step within +-2 of the cited step
  miss  : none of the above
Normalisation: lowercase; all quote characters (' " ` and curly variants) removed;
whitespace collapsed; trailing ellipsis/punctuation stripped.

Cited step per field: t_err_evidence->t_err, t_commit_evidence->t_commit,
t_surface_evidence->t_surface, forewarning_evidence->forewarning_first_step,
fabrication_evidence->fabrication_onset_step, first_error_evidence->first_error_step,
verification_evidence->first_relevant_verification_step.  near_miss_evidence and
suspicious_pass_evidence have no linked step field: the first "Step N" mentioned in
the quote is used; if none, the whole trajectory is searched (cited_step=None,
category is exact/fuzzy/miss only; recorded as search_scope='whole').

Supplementary diagnostic (not part of the four categories): quoted_fragment_hit =
at least one sub-string enclosed in quotes/backticks inside the evidence text
(>=3 tokens) is found verbatim in the cited step (+-0).  Many evidence strings are
"Step N: <paraphrase> '<verbatim fragment>'" so this measures whether the
verbatim part is grounded even when the wrapper is not.
"""
import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_common as C  # noqa: E402

FIELD_STEP = {
    't_err_evidence': 't_err', 't_commit_evidence': 't_commit', 't_surface_evidence': 't_surface',
    'forewarning_evidence': 'forewarning_first_step', 'fabrication_evidence': 'fabrication_onset_step',
    'first_error_evidence': 'first_error_step', 'verification_evidence': 'first_relevant_verification_step',
    'near_miss_evidence': None, 'suspicious_pass_evidence': None,
}
QUOTE_CHARS = re.compile(r'[\'"`‘’“”´]')
WS = re.compile(r'\s+')
TOK = re.compile(r'[a-z0-9_./-]+')
STEP_MENTION = re.compile(r'\bsteps?\s*#?(\d+)', re.I)
FRAG_RE = re.compile(r'`([^`]{6,})`|"([^"]{6,})"|“([^”]{6,})”|\'([^\']{6,})\'|‘([^’]{6,})’')
JACCARD_THRESH = 0.8


def norm(s):
    s = QUOTE_CHARS.sub('', s.lower())
    s = WS.sub(' ', s).strip()
    s = s.strip(' .;:,…-')
    s = re.sub(r'\.\.\.$', '', s).strip()
    return s


def toks(s):
    return TOK.findall(s)


def best_jaccard(qtoks, ttoks):
    """Max token-set Jaccard over sliding windows of size k and int(1.5k)."""
    qset = set(qtoks)
    if not qset or not ttoks:
        return 0.0
    best = 0.0
    n = len(ttoks)
    for k in sorted({max(3, len(qtoks)), max(3, int(1.5 * len(qtoks)))}):
        if n <= k:
            wset = set(ttoks)
            j = len(wset & qset) / len(wset | qset)
            best = max(best, j)
            continue
        cnt = collections.Counter(ttoks[:k])
        inter = sum(1 for t in cnt if t in qset)
        union = len(qset) + sum(1 for t in cnt if t not in qset)
        best = max(best, inter / union)
        for r in range(k, n):
            add, rem = ttoks[r], ttoks[r - k]
            if add != rem:
                cnt[add] += 1
                if cnt[add] == 1:
                    if add in qset:
                        inter += 1
                    else:
                        union += 1
                cnt[rem] -= 1
                if cnt[rem] == 0:
                    del cnt[rem]
                    if rem in qset:
                        inter -= 1
                    else:
                        union -= 1
            j = inter / union
            if j > best:
                best = j
                if best >= 1.0:
                    return best
    return best


STOP = set('the a an and or of to in on at for with from by is are was were be been being this that these those it its as not no but then than after before step steps agent output shows show which when while into out over via also only just'.split())


def content_tokens(qt):
    """Quote tokens that carry content: >=4 chars, not stopwords, not pure 'step N' numbers."""
    return [t for t in qt if len(t) >= 4 and t not in STOP]


def match_in_text(qn, qt, text_norm, text_toks):
    if qn and qn in text_norm:
        return 'exact', 1.0
    j = best_jaccard(qt, text_toks)
    if j >= JACCARD_THRESH:
        return 'fuzzy', j
    return None, j


def fragments(quote):
    out = []
    for m in FRAG_RE.finditer(quote):
        f = next(g for g in m.groups() if g)
        if len(toks(norm(f))) >= 3:
            out.append(norm(f))
    return out


def main():
    ann = C.load_annotations()
    rows, misses = [], []
    cache = {}

    def step_text(cid, i):
        key = (cid, i)
        if key not in cache:
            steps, _ = C.load_traj(cid)
            if 1 <= i <= len(steps):
                raw = steps[i - 1]['all_text']
            else:
                raw = ''
            tn = norm(raw)
            cache[key] = (tn, toks(tn))
        return cache[key]

    for rec in ann:
        cid = rec['case_id']
        task, sc, mo = C.split_case(cid)
        kind = 'FAIL' if C.is_fail(rec) else 'PASS'
        steps, _ = C.load_traj(cid)
        m = len(steps)
        for field, stepfield in FIELD_STEP.items():
            q = rec.get(field)
            if not q or not str(q).strip():
                continue
            q = str(q)
            cited = rec.get(stepfield) if stepfield else None
            mention = STEP_MENTION.search(q)
            mentioned = int(mention.group(1)) if mention else None
            scope = 'cited'
            if cited is None:
                if mentioned is not None:
                    cited, scope = mentioned, 'mentioned'
                else:
                    scope = 'whole'
            qn = norm(q)
            qt = toks(qn)
            cat, score, found_step = 'miss', 0.0, None
            frag_hit = False
            frags = fragments(q)
            ctoks = content_tokens(qt)
            recall = None
            if scope != 'whole' and 1 <= cited <= m:
                tn, tt = step_text(cid, cited)
                c, j = match_in_text(qn, qt, tn, tt)
                score = j
                if ctoks:
                    tset = set(tt)
                    recall = round(sum(1 for t in ctoks if t in tset) / len(ctoks), 3)
                if c:
                    cat, found_step = c, cited
                else:
                    for off in (1, -1, 2, -2):
                        k = cited + off
                        if 1 <= k <= m:
                            tn2, tt2 = step_text(cid, k)
                            c2, j2 = match_in_text(qn, qt, tn2, tt2)
                            if c2:
                                cat, found_step, score = 'near', k, j2
                                break
                            score = max(score, j2)
                frag_hit = any(f in tn for f in frags)
            elif scope == 'whole':
                for k in range(1, m + 1):
                    tn, tt = step_text(cid, k)
                    c, j = match_in_text(qn, qt, tn, tt)
                    score = max(score, j)
                    if not frag_hit and any(f in tn for f in frags):
                        frag_hit = True
                    if c:
                        cat, found_step = c, k
                        break
            else:
                cat = 'miss'
                scope = 'cited_out_of_range'
            row = {'case_id': cid, 'kind': kind, 'scaffold': sc, 'model': mo, 'field': field,
                   'cited_step': cited, 'mentioned_step': mentioned, 'search_scope': scope,
                   'category': cat, 'found_step': found_step, 'best_jaccard': round(score, 3),
                   'n_quoted_fragments': len(frags), 'quoted_fragment_hit': frag_hit,
                   'step_mismatch': (mentioned is not None and stepfield is not None and rec.get(stepfield) is not None and mentioned != rec.get(stepfield)),
                   'quote_len_tokens': len(qt), 'content_token_recall': recall}
            rows.append(row)
            if cat == 'miss':
                misses.append({'case_id': cid, 'kind': kind, 'field': field, 'cited_step': cited,
                               'mentioned_step': mentioned, 'best_jaccard': round(score, 3),
                               'quoted_fragment_hit': frag_hit, 'content_token_recall': recall, 'quote': q})

    def dist(sub):
        n = len(sub)
        c = collections.Counter(r['category'] for r in sub)
        return {'n': n, 'exact': c['exact'], 'fuzzy': c['fuzzy'], 'near': c['near'], 'miss': c['miss'],
                'exact_pct': C.pct(c['exact'], n), 'fuzzy_pct': C.pct(c['fuzzy'], n), 'near_pct': C.pct(c['near'], n),
                'miss_pct': C.pct(c['miss'], n),
                'located_pct': C.pct(n - c['miss'], n),
                'miss_but_fragment_hit': sum(1 for r in sub if r['category'] == 'miss' and r['quoted_fragment_hit']),
                'located_or_fragment_pct': C.pct(sum(1 for r in sub if r['category'] != 'miss' or r['quoted_fragment_hit']), n),
                'step_mismatch': sum(1 for r in sub if r['step_mismatch']),
                'content_recall_mean': (round(sum(r['content_token_recall'] for r in sub if r['content_token_recall'] is not None) / max(1, sum(1 for r in sub if r['content_token_recall'] is not None)), 3) if any(r['content_token_recall'] is not None for r in sub) else None),
                'content_recall_ge50_pct': C.pct(sum(1 for r in sub if (r['content_token_recall'] or 0) >= 0.5), sum(1 for r in sub if r['content_token_recall'] is not None)),
                'content_recall_ge70_pct': C.pct(sum(1 for r in sub if (r['content_token_recall'] or 0) >= 0.7), sum(1 for r in sub if r['content_token_recall'] is not None)),
                'content_recall_lt30_pct': C.pct(sum(1 for r in sub if r['content_token_recall'] is not None and r['content_token_recall'] < 0.3), sum(1 for r in sub if r['content_token_recall'] is not None))}

    summary = {'overall': dist(rows), 'by_field': {}, 'by_scaffold': {}, 'by_model': {}, 'by_kind': {},
               'by_scaffold_x_field_miss_pct': {}, 'by_model_x_field_miss_pct': {},
               'rules': {'normalisation': 'lowercase; strip quote chars; collapse whitespace; strip trailing punctuation',
                         'exact': 'normalised quote substring of normalised (command+agent_analysis+terminal_result)',
                         'fuzzy': 'token-set Jaccard >= %.2f on best sliding window (|q| and 1.5|q| tokens)' % JACCARD_THRESH,
                         'near': 'exact/fuzzy in step +-1 or +-2', 'miss': 'otherwise',
                         'fragment': 'any quoted/backticked substring (>=3 tokens) found verbatim in cited step'}}
    for f in FIELD_STEP:
        summary['by_field'][f] = dist([r for r in rows if r['field'] == f])
    for sc in C.SCAFFOLDS:
        summary['by_scaffold'][sc] = dist([r for r in rows if r['scaffold'] == sc])
        summary['by_scaffold_x_field_miss_pct'][sc] = {f: dist([r for r in rows if r['scaffold'] == sc and r['field'] == f])['miss_pct'] for f in FIELD_STEP}
    for mo in C.MODELS:
        summary['by_model'][mo] = dist([r for r in rows if r['model'] == mo])
        summary['by_model_x_field_miss_pct'][mo] = {f: dist([r for r in rows if r['model'] == mo and r['field'] == f])['miss_pct'] for f in FIELD_STEP}
    for k in ('FAIL', 'PASS'):
        summary['by_kind'][k] = dist([r for r in rows if r['kind'] == k])
    summary['by_scope'] = {s: dist([r for r in rows if r['search_scope'] == s]) for s in sorted(set(r['search_scope'] for r in rows))}
    C.write_json(os.path.join(C.OUT_DIR, 'evidence_hits.json'), {'summary': summary, 'rows': rows})
    with open(os.path.join(C.OUT_DIR, 'evidence_miss.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['case_id', 'kind', 'field', 'cited_step', 'mentioned_step', 'best_jaccard', 'quoted_fragment_hit', 'content_token_recall', 'quote'])
        w.writeheader()
        w.writerows(misses)
    print(json.dumps(summary['overall'], indent=1))
    for f, v in summary['by_field'].items():
        print('%-26s n=%5d exact %5.1f fuzzy %5.1f near %5.1f miss %5.1f  frag-rescue %4d  recall-mean %s ge50 %s lt30 %s' % (f, v['n'], v['exact_pct'], v['fuzzy_pct'], v['near_pct'], v['miss_pct'], v['miss_but_fragment_hit'], v['content_recall_mean'], v['content_recall_ge50_pct'], v['content_recall_lt30_pct']))
    for sc, v in summary['by_scaffold'].items():
        print('%-12s n=%5d exact %5.1f fuzzy %5.1f near %5.1f miss %5.1f' % (sc, v['n'], v['exact_pct'], v['fuzzy_pct'], v['near_pct'], v['miss_pct']))
    for mo, v in summary['by_model'].items():
        print('%-14s n=%5d exact %5.1f fuzzy %5.1f near %5.1f miss %5.1f' % (mo, v['n'], v['exact_pct'], v['fuzzy_pct'], v['near_pct'], v['miss_pct']))


if __name__ == '__main__':
    main()
