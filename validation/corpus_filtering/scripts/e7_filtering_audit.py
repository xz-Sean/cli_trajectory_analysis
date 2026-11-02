#!/usr/bin/env python3
"""E7 step 3: task-filtering audit (full benchmark vs retained 89) and trajectory accounting.

Usage: python3 e7_filtering_audit.py <tb_task_metadata.csv> <merged_tasks.json>
                                     <merged_trajectories dir> <traj_data_v2_all89tasks.json>
                                     <out md> <out json>
"""
import csv, json, os, re, sys, collections, math

tb_csv, merged_json, mt_dir, traj_json, out_md, out_json = sys.argv[1:7]
try:
    from scipy.stats import chi2_contingency, chi2 as chi2_dist
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

NORM_CAT = {"game": "games", "math": "mathematics", "file_operations": "file-operations"}
def norm_cat(c): c = (c or "").strip(); return NORM_CAT.get(c, c)

SCAFFOLDS = ["miniswe", "openhands", "terminus2"]
MODELS = ["claude", "deepseek-v3.2", "gpt5", "kimi", "qwen", "devstral", "gemini"]

# ---- task metadata (pinned checkout) ----
tb = {}
with open(tb_csv, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["has_task_yaml"] == "1":
            tb[r["task"]] = dict(category=r["category"].strip(), difficulty=r["difficulty"].strip())
retained = sorted(t["task_id"] for t in json.load(open(merged_json)))
assert len(retained) == 89
missing_from_pin = [t for t in retained if t not in tb]
dropped = sorted(t for t in tb if t not in retained)

def dist(tasks, field, norm=False):
    c = collections.Counter()
    for t in tasks:
        v = tb.get(t, {}).get(field, "<not in pinned checkout>")
        c[norm_cat(v) if (norm and field == "category") else v] += 1
    return c

cat_all, cat_ret, cat_drop = (dist(x, "category", True) for x in (list(tb), retained, dropped))
cat_all_raw = dist(list(tb), "category", False)
dif_all, dif_ret, dif_drop = (dist(x, "difficulty") for x in (list(tb), retained, dropped))

# ---- chi-square (manual + scipy) ----
def chi_square(table):
    """table: list of rows (lists of counts). returns chi2, dof, expected, p (p only with scipy)."""
    R = len(table); C = len(table[0])
    rs = [sum(r) for r in table]; cs = [sum(table[i][j] for i in range(R)) for j in range(C)]; N = sum(rs)
    exp = [[rs[i] * cs[j] / N for j in range(C)] for i in range(R)]
    stat = sum((table[i][j] - exp[i][j]) ** 2 / exp[i][j] for i in range(R) for j in range(C) if exp[i][j] > 0)
    dof = (R - 1) * (C - 1)
    # chi-square survival function via regularized upper incomplete gamma (series/continued fraction)
    def gammainc_upper(a, x):
        if x <= 0: return 1.0
        if x < a + 1:
            s = term = 1.0 / a; n = 1
            while abs(term) > 1e-15 * abs(s) and n < 10000:
                term *= x / (a + n); s += term; n += 1
            return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
        # Lentz continued fraction
        b = x + 1 - a; c = 1e300; d = 1 / b; h = d
        for i in range(1, 10000):
            an = -i * (i - a); b += 2
            d = an * d + b; d = 1e-300 if abs(d) < 1e-300 else d
            c = b + an / c; c = 1e-300 if abs(c) < 1e-300 else c
            d = 1 / d; delta = d * c; h *= delta
            if abs(delta - 1) < 1e-15: break
        return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    p = gammainc_upper(dof / 2, stat / 2)
    return stat, dof, exp, p

levels = ["easy", "medium", "hard"]
table = [[dif_ret.get(l, 0) for l in levels], [dif_drop.get(l, 0) for l in levels]]
stat, dof, exp, p_manual = chi_square(table)
p_scipy = None
if HAVE_SCIPY:
    s2, p_scipy, d2, _ = chi2_contingency(table, correction=False)
    assert abs(s2 - stat) < 1e-9 and d2 == dof
# Cramer's V
N = sum(map(sum, table)); cramers_v = math.sqrt(stat / (N * (min(len(table), len(levels)) - 1)))
# ordinal view: mean difficulty index (easy=1, medium=2, hard=3) and share hard
def share(c, l): n = sum(c.get(x, 0) for x in levels); return c.get(l, 0) / n if n else float("nan")

# category chi-square (sparse; report with caveat), over normalised categories present in either group
cats_sorted = [c for c, _ in cat_all.most_common()]
cat_table = [[cat_ret.get(c, 0) for c in cats_sorted], [cat_drop.get(c, 0) for c in cats_sorted]]
cstat, cdof, cexp, cp_manual = chi_square(cat_table)
cat_small_exp = sum(1 for row in cexp for e in row if e < 5)
cp_scipy = chi2_contingency(cat_table, correction=False)[1] if HAVE_SCIPY else None

# ---- trajectory accounting ----
traj = json.load(open(traj_json))
analyzed = {r["case_id"]: ("FAIL" if "t_err" in r else "PASS") for r in traj}
grid = [f"{t}__{s}__{m}" for t in retained for s in SCAFFOLDS for m in MODELS]
leaves = {}
for t in retained:
    for s in SCAFFOLDS:
        for m in MODELS:
            q = os.path.join(mt_dir, t, s, m)
            if os.path.isdir(q):
                txt = open(os.path.join(q, "summary.md"), encoding="utf-8").read()
                ir = re.search(r"is_resolved:\*\* (\S+)", txt)
                steps = re.search(r"Total Steps:\*\* (\d+)", txt)
                leaves[f"{t}__{s}__{m}"] = dict(is_resolved=ir.group(1) if ir else "<absent>",
                                                total_steps=int(steps.group(1)) if steps else None,
                                                trial_name=(re.search(r"trial_name:\*\* (\S+)", txt) or [None, None])[1],
                                                path=q)
extra_leaves = sorted(set(leaves) - set(grid))
missing_leaves = [c for c in grid if c not in leaves]
excluded = sorted(c for c in leaves if c not in analyzed)
not_in_leaves = sorted(c for c in analyzed if c not in leaves)

SUBMIT_MARKERS = ["COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT", '"task_complete": true', "task_complete\": true",
                  "AgentFinishAction", "finish(", "<finish>"]
def last_step_info(info, scaffold):
    n = info["total_steps"]
    if not n: return dict(agent_submitted=None, last_step_excerpt="")
    p = os.path.join(info["path"], f"step_{n}.md")
    if not os.path.exists(p): return dict(agent_submitted=None, last_step_excerpt="<no last step file>")
    txt = open(p, encoding="utf-8", errors="replace").read()
    # only mini-swe-agent writes an explicit submit command into the transcript; the local export of
    # terminus2/openhands does not preserve the agent's task_complete/finish flag, so leave those as None
    sub = any(mk in txt for mk in SUBMIT_MARKERS) if scaffold == "miniswe" else None
    m = re.search(r"## Command\s*```[a-z]*\n(.*?)```", txt, re.S)
    cmd = (m.group(1).strip().splitlines() or [""])[0][:80] if m else ""
    return dict(agent_submitted=sub, last_command=cmd)

excluded_rows = []
for c in excluded:
    info = leaves[c]
    t, s, m = c.split("__")
    ex = last_step_info(info, s)
    reason = {"None": "no outcome recorded (is_resolved=None)",
              "Unknown": "no outcome recorded (is_resolved=Unknown)"}.get(info["is_resolved"], f"is_resolved={info['is_resolved']}")
    excluded_rows.append(dict(case_id=c, task=t, scaffold=s, model=m, is_resolved=info["is_resolved"],
                              total_steps=info["total_steps"], agent_submitted=ex.get("agent_submitted"),
                              last_command=ex.get("last_command", ""), reason=reason))
excl_by_sm = collections.Counter((r["scaffold"], r["model"]) for r in excluded_rows)
excl_by_task = collections.Counter(r["task"] for r in excluded_rows)
excl_by_ir = collections.Counter(r["is_resolved"] for r in excluded_rows)
excl_by_submit = collections.Counter(str(r["agent_submitted"]) for r in excluded_rows)

# consistency between summary.md is_resolved and the analysed label
ir_vs_label = collections.Counter((leaves[c]["is_resolved"], lab) for c, lab in analyzed.items() if c in leaves)
inconsistent = sorted(c for c, lab in analyzed.items() if c in leaves and
                      leaves[c]["is_resolved"] not in ({"PASS": "True", "FAIL": "False"}[lab],))

per_sm_analyzed = collections.Counter(tuple(c.split("__")[1:]) for c in analyzed)
per_sm_leaves = collections.Counter(tuple(c.split("__")[1:]) for c in leaves)
missing_by_sm = collections.Counter(tuple(c.split("__")[1:]) for c in missing_leaves)

paper = dict(grid=1869, analyzed=1794, unavailable=75, fail=1184, pass_=610, raw_pool=3843, raw_total=5040)
acct = dict(grid=len(grid), leaves_present=len(leaves), extra_leaves=extra_leaves, missing_leaves=missing_leaves,
            n_missing=len(missing_leaves), analyzed=len(analyzed), n_excluded=len(excluded),
            analyzed_not_in_leaves=not_in_leaves,
            fail=sum(1 for v in analyzed.values() if v == "FAIL"), pass_=sum(1 for v in analyzed.values() if v == "PASS"),
            paper=paper, missing_plus_excluded=len(missing_leaves) + len(excluded),
            equals_paper_75=(len(missing_leaves) + len(excluded)) == paper["unavailable"],
            excluded_by_is_resolved=dict(excl_by_ir), excluded_by_agent_submitted=dict(excl_by_submit),
            excluded_by_scaffold=dict(collections.Counter(r["scaffold"] for r in excluded_rows)),
            excluded_by_model=dict(collections.Counter(r["model"] for r in excluded_rows)),
            excluded_by_scaffold_model={f"{s}/{m}": n for (s, m), n in sorted(excl_by_sm.items())},
            excluded_by_task=dict(excl_by_task.most_common()),
            is_resolved_vs_analyzed_label={f"{a}->{b}": n for (a, b), n in ir_vs_label.items()},
            analyzed_with_inconsistent_is_resolved=inconsistent,
            per_scaffold_model=[dict(scaffold=s, model=m, grid=len(retained), leaves=per_sm_leaves[(s, m)],
                                     missing=missing_by_sm[(s, m)], excluded=excl_by_sm[(s, m)],
                                     analyzed=per_sm_analyzed[(s, m)]) for s in SCAFFOLDS for m in MODELS],
            excluded_cases=excluded_rows)

res = dict(
    pinned_checkout=dict(n_tasks=len(tb), n_categories_raw=len(cat_all_raw), n_categories_normalised=len(cat_all),
                         n_difficulty_levels=len(dif_all), category_counts_raw=dict(cat_all_raw.most_common()),
                         category_counts_normalised=dict(cat_all.most_common()), difficulty_counts=dict(dif_all)),
    retained_89=dict(n=len(retained), not_in_pinned_checkout=missing_from_pin, n_categories_normalised=len(cat_ret),
                     category_counts=dict(cat_ret.most_common()), difficulty_counts=dict(dif_ret)),
    dropped=dict(n=len(dropped), n_categories_normalised=len(cat_drop), category_counts=dict(cat_drop.most_common()),
                 difficulty_counts=dict(dif_drop), tasks=dropped),
    categories_only_in_dropped=sorted(set(cat_drop) - set(cat_ret)),
    difficulty_chi_square=dict(levels=levels, table_retained=table[0], table_dropped=table[1], chi2=stat, dof=dof,
                               p_manual=p_manual, p_scipy=p_scipy, expected=exp, cramers_v=cramers_v,
                               share_hard_retained=share(dif_ret, "hard"), share_hard_dropped=share(dif_drop, "hard"),
                               share_easy_retained=share(dif_ret, "easy"), share_easy_dropped=share(dif_drop, "easy")),
    category_chi_square=dict(categories=cats_sorted, table_retained=cat_table[0], table_dropped=cat_table[1], chi2=cstat,
                             dof=cdof, p_manual=cp_manual, p_scipy=cp_scipy, n_cells_expected_lt5=cat_small_exp,
                             n_cells=2 * len(cats_sorted), caveat="many expected counts < 5; treat as descriptive"),
    trajectory_accounting=acct,
    raw_pool_note="The 3,843/5,040 raw completion pool (pre-filter, all 240 tasks) is not available locally; "
                  "per scaffold x model raw completion rates cannot be recomputed here.")
json.dump(res, open(out_json, "w"), indent=1)

# ---- markdown ----
L = ["# E7 task-filtering audit\n",
     f"Pinned Terminal-Bench checkout: {len(tb)} tasks with `task.yaml` (see `resub/tb_tasks/TB_COMMIT.txt`). "
     f"Retained (paper) tasks: {len(retained)}; dropped: {len(dropped)}. "
     + (f"Retained tasks absent from the pinned checkout: {missing_from_pin}. " if missing_from_pin else
        "All 89 retained tasks exist in the pinned checkout. ")
     + f"Raw `category` strings: {len(cat_all_raw)} distinct; after normalising obvious spelling variants "
       f"(game->games, math->mathematics, file_operations->file-operations): {len(cat_all)}. "
       f"Difficulty levels: {len(dif_all)} ({', '.join(dif_all)}).\n",
     "## Category distribution (task level, normalised categories)\n",
     "| category | all tasks | retained 89 | dropped | retention rate |", "|---|---|---|---|---|"]
for c, n in cat_all.most_common():
    L.append(f"| {c} | {n} | {cat_ret.get(c,0)} | {cat_drop.get(c,0)} | {cat_ret.get(c,0)/n:.0%} |")
L.append(f"| **total** | {sum(cat_all.values())} | {sum(cat_ret.values())} | {sum(cat_drop.values())} | {sum(cat_ret.values())/sum(cat_all.values()):.0%} |")
L.append(f"\nCategories present in the benchmark but absent from the retained set: {', '.join(sorted(set(cat_drop)-set(cat_ret))) or 'none'} "
         f"({len(cat_ret)} of {len(cat_all)} normalised categories retained).\n")
L.append(f"Category chi-square retained vs dropped (descriptive only, {cat_small_exp}/{2*len(cats_sorted)} cells have expected < 5): "
         f"chi2 = {cstat:.2f}, dof = {cdof}, p = {cp_manual:.3g}.\n")
L += ["## Difficulty distribution (task level)\n",
      "| difficulty | all tasks | retained 89 | dropped | retention rate |", "|---|---|---|---|---|"]
for l in levels:
    L.append(f"| {l} | {dif_all.get(l,0)} | {dif_ret.get(l,0)} | {dif_drop.get(l,0)} | {dif_ret.get(l,0)/dif_all.get(l,1):.0%} |")
L.append(f"| share hard | {share(dif_all,'hard'):.1%} | {share(dif_ret,'hard'):.1%} | {share(dif_drop,'hard'):.1%} | |")
L.append(f"\nChi-square test of independence, difficulty x (retained, dropped): chi2 = {stat:.3f}, dof = {dof}, "
         f"p = {p_manual:.4f} (manual)" + (f", p = {p_scipy:.4f} (scipy)" if p_scipy is not None else "")
         + f"; Cramer's V = {cramers_v:.3f}. Expected counts retained: {[round(e,1) for e in exp[0]]}, dropped: {[round(e,1) for e in exp[1]]}.\n")
L += ["## Trajectory accounting\n",
      "| stage | count | note |", "|---|---|---|",
      f"| full grid 89 x 3 x 7 | {len(grid)} | paper: {paper['grid']} |",
      f"| leaves present locally | {len(leaves)} | {len(missing_leaves)} grid cells have no trajectory at source |",
      f"| analysed records | {len(analyzed)} | paper: {paper['analyzed']} ({acct['fail']} FAIL + {acct['pass_']} PASS; paper {paper['fail']}+{paper['pass_']}) |",
      f"| present but excluded | {len(excluded)} | by is_resolved: {dict(excl_by_ir)} |",
      f"| missing + excluded | {len(missing_leaves)+len(excluded)} | paper says {paper['unavailable']} unavailable: "
      f"{'EQUAL' if acct['equals_paper_75'] else 'NOT equal'} |",
      "\n### The missing grid cells (no trajectory at source)\n"]
L += [f"- {c}" for c in missing_leaves]
L.append("\n### Present-but-excluded leaves\n")
L.append("`summary.md` carries only `is_resolved` (True/False/None/Unknown); no timeout/abnormal-termination field exists "
         "in the local export, so the reason is recorded as the missing verdict. `agent_submitted` is a heuristic available only "
         "for mini-swe-agent, whose transcript contains an explicit COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT command (True = agent ended "
         "normally; False = transcript ends without a submit, consistent with a step/time cap or harness abort). The local export "
         "of terminus2/openhands does not preserve the agent completion flag, so it is None there.\n")
L.append(f"By scaffold: {acct['excluded_by_scaffold']}; by model: {acct['excluded_by_model']}; agent_submitted: {dict(excl_by_submit)}.\n")
L.append(f"Excluded by task: " + ", ".join(f"{t} ({n})" for t, n in excl_by_task.most_common()) + "\n")
L += ["| case_id | is_resolved | steps | agent_submitted | last command | reason |", "|---|---|---|---|---|---|"]
for r in excluded_rows:
    L.append(f"| {r['case_id']} | {r['is_resolved']} | {r['total_steps']} | {r['agent_submitted']} | `{r['last_command'].replace('|','\\|')}` | {r['reason']} |")
L.append("\n### Consistency check: summary.md `is_resolved` vs analysed label\n")
L.append(f"{acct['is_resolved_vs_analyzed_label']}")
if inconsistent:
    L.append(f"\n{len(inconsistent)} analysed records are labelled FAIL although `summary.md` has no verdict (is_resolved=None): "
             + ", ".join(inconsistent) + ". These were kept in the 1,794 while the 66 above were dropped; the paper's "
             "'failed execution' boundary is therefore not exactly the `is_resolved is None/Unknown` boundary.\n")
L += ["\n### Per scaffold x model\n", "| scaffold | model | grid | leaves | missing | excluded | analysed |", "|---|---|---|---|---|---|---|"]
for r in acct["per_scaffold_model"]:
    L.append(f"| {r['scaffold']} | {r['model']} | {r['grid']} | {r['leaves']} | {r['missing']} | {r['excluded']} | {r['analyzed']} |")
L.append(f"\n{res['raw_pool_note']}\n")
open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:40]))
print("...\n", json.dumps({k: res["trajectory_accounting"][k] for k in ("grid","leaves_present","n_missing","analyzed","n_excluded","missing_plus_excluded","equals_paper_75","excluded_by_is_resolved","excluded_by_agent_submitted","is_resolved_vs_analyzed_label")}, indent=1))
