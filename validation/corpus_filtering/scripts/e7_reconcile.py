#!/usr/bin/env python3
"""E7 step 2: reconcile task metadata across three sources for the 89 paper tasks.

Usage: python3 e7_reconcile.py <tb_task_metadata.csv> <merged_tasks.json>
                               <terminal_bench_task_stats.md> <traj_data_v2_all89tasks.json>
                               <out md> <out json>
"""
import csv, json, re, sys, collections

tb_csv, merged_json, stats_md, traj_json, out_md, out_json = sys.argv[1:7]

NORM_CAT = {"game": "games", "math": "mathematics", "file_operations": "file-operations"}
def norm_cat(c):
    c = (c or "").strip()
    return NORM_CAT.get(c, c)

tb = {}
with open(tb_csv, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["has_task_yaml"] == "1":
            tb[r["task"]] = dict(category=r["category"].strip(), difficulty=r["difficulty"].strip())

merged = {}
for t in json.load(open(merged_json)):
    merged[t["task_id"]] = dict(category=(t.get("category") or "").strip(),
                                difficulty=(t.get("difficulty") or "").strip())

stats = {}
in_table = False
for line in open(stats_md, encoding="utf-8"):
    if line.startswith("## Per-Task Details"):
        in_table = True
        continue
    if in_table and line.startswith("|"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] not in ("Task ID", "") and not set(cells[0]) <= set("-: "):
            stats[cells[0]] = dict(category=cells[1], difficulty=cells[2])

traj = json.load(open(traj_json))
tasks89 = sorted(merged)
assert len(tasks89) == 89, len(tasks89)

src = {"pinned_task_yaml": tb, "merged_tasks.json": merged, "task_stats.md": stats}
coverage = {k: sum(1 for t in tasks89 if t in v) for k, v in src.items()}

disagreements = []
for t in tasks89:
    for field in ("category", "difficulty"):
        vals = {k: v.get(t, {}).get(field, "<missing>") for k, v in src.items()}
        if len(set(vals.values())) > 1:
            disagreements.append(dict(task=t, field=field, **vals))

# pairwise disagreement counts (on the 89 tasks)
pairs = [("pinned_task_yaml", "merged_tasks.json"), ("pinned_task_yaml", "task_stats.md"),
         ("merged_tasks.json", "task_stats.md")]
pairwise = {}
for a, b in pairs:
    for field in ("category", "difficulty"):
        n = sum(1 for t in tasks89 if t in src[a] and t in src[b]
                and src[a][t][field] != src[b][t][field])
        n_norm = sum(1 for t in tasks89 if t in src[a] and t in src[b]
                     and (norm_cat(src[a][t][field]) if field == "category" else src[a][t][field])
                     != (norm_cat(src[b][t][field]) if field == "category" else src[b][t][field]))
        pairwise[f"{a} vs {b} / {field}"] = dict(raw=n, normalized=n_norm)

# distinct categories among the 89 under each source
distinct = {}
task_level_diff = {}
traj_level_diff = {}
for k, v in src.items():
    cats = collections.Counter(v.get(t, {}).get("category", "<missing>") for t in tasks89)
    distinct[k] = dict(raw=len(cats), normalized=len({norm_cat(c) for c in cats}), counts=dict(cats.most_common()))
    task_level_diff[k] = dict(collections.Counter(v.get(t, {}).get("difficulty", "<missing>") for t in tasks89))
    c = collections.Counter()
    c_fail = collections.Counter(); c_pass = collections.Counter()
    for r in traj:
        t = r["case_id"].split("__")[0]
        d = v.get(t, {}).get("difficulty", "<missing>")
        c[d] += 1
        (c_fail if "t_err" in r else c_pass)[d] += 1
    traj_level_diff[k] = dict(all=dict(c), fail=dict(c_fail), pass_=dict(c_pass))

paper = dict(easy=459, medium=742, hard=593, n_categories=16)
match = {k: all(traj_level_diff[k]["all"].get(d, 0) == paper[d] for d in ("easy", "medium", "hard"))
         for k in src}

res = dict(n_tasks=len(tasks89), coverage=coverage, pairwise_disagreements=pairwise,
           disagreements=disagreements, distinct_categories_89=distinct,
           task_level_difficulty_89=task_level_diff, traj_level_difficulty_1794=traj_level_diff,
           paper_claim=paper, traj_level_matches_paper=match, n_traj=len(traj))
json.dump(res, open(out_json, "w"), indent=1)

L = []
L.append("# E7 metadata reconciliation (89 paper tasks)\n")
L.append("Sources: (A) `task.yaml` from the pinned Terminal-Bench checkout "
         "(`resub/tb_tasks/TB_COMMIT.txt`), (B) `merged_tasks.json` (the paper's task table), "
         "(C) `terminal_bench_task_stats.md` (older local 241-task table).\n")
L.append(f"Coverage of the 89 tasks: {coverage}\n")
L.append("## Pairwise disagreement counts (89 tasks)\n")
L.append("| comparison | raw | after category normalisation (game->games, math->mathematics, file_operations->file-operations) |")
L.append("|---|---|---|")
for k, v in pairwise.items():
    L.append(f"| {k} | {v['raw']} | {v['normalized']} |")
L.append("\n## Every disagreement (any source differs)\n")
L.append("| task | field | pinned task.yaml | merged_tasks.json | task_stats.md |")
L.append("|---|---|---|---|---|")
for d in disagreements:
    L.append(f"| {d['task']} | {d['field']} | {d['pinned_task_yaml']} | {d['merged_tasks.json']} | {d['task_stats.md']} |")
L.append(f"\nTotal disagreement rows: {len(disagreements)} "
         f"({sum(1 for d in disagreements if d['field']=='category')} category, "
         f"{sum(1 for d in disagreements if d['field']=='difficulty')} difficulty).\n")
L.append("## Which source do the paper's numbers correspond to?\n")
L.append("### Distinct categories among the 89 tasks\n")
L.append("| source | distinct (raw) | distinct (normalised) |")
L.append("|---|---|---|")
for k, v in distinct.items():
    L.append(f"| {k} | {v['raw']} | {v['normalized']} |")
L.append(f"\nPaper claims {paper['n_categories']} categories.\n")
for k, v in distinct.items():
    L.append(f"- {k}: " + ", ".join(f"{c} ({n})" for c, n in v["counts"].items()))
L.append("\n### Task-level difficulty of the 89 tasks\n")
L.append("| source | easy | medium | hard | other |")
L.append("|---|---|---|---|---|")
for k, v in task_level_diff.items():
    other = {a: b for a, b in v.items() if a not in ("easy", "medium", "hard")}
    L.append(f"| {k} | {v.get('easy',0)} | {v.get('medium',0)} | {v.get('hard',0)} | {other or ''} |")
L.append(f"\n### Trajectory-level difficulty over the {len(traj)} analysed records "
         f"(paper: {paper['easy']} easy / {paper['medium']} medium / {paper['hard']} hard)\n")
L.append("| source | easy | medium | hard | other | matches paper |")
L.append("|---|---|---|---|---|---|")
for k, v in traj_level_diff.items():
    a = v["all"]; other = {x: y for x, y in a.items() if x not in ("easy", "medium", "hard")}
    L.append(f"| {k} | {a.get('easy',0)} | {a.get('medium',0)} | {a.get('hard',0)} | {other or ''} | {'YES' if match[k] else 'no'} |")
L.append("\nSplit by outcome (FAIL = record has `t_err`):\n")
L.append("| source | easy F/P | medium F/P | hard F/P |")
L.append("|---|---|---|---|")
for k, v in traj_level_diff.items():
    L.append(f"| {k} | {v['fail'].get('easy',0)}/{v['pass_'].get('easy',0)} | "
             f"{v['fail'].get('medium',0)}/{v['pass_'].get('medium',0)} | "
             f"{v['fail'].get('hard',0)}/{v['pass_'].get('hard',0)} |")
L.append("\nHow difficulty is determined: it is the `difficulty` field that each task author wrote in "
         "`task.yaml` (values easy/medium/hard; no rubric is enforced by the benchmark). The paper's "
         "trajectory-level counts simply attach each task's label to every one of its analysed trajectories.\n")

# ---- sanity check on task_stats.md itself: its per-task table vs its own header marginals and vs pinned (all tasks)
all_tb = sorted(tb)
st_common = [t for t in all_tb if t in stats]
st_cat_dis = sum(1 for t in st_common if stats[t]["category"] != tb[t]["category"])
st_dif_dis = sum(1 for t in st_common if stats[t]["difficulty"] != tb[t]["difficulty"])
st_marg_dif = collections.Counter(v["difficulty"] for v in stats.values())
st_marg_cat = collections.Counter(v["category"] for v in stats.values())
tb_marg_dif = collections.Counter(v["difficulty"] for v in tb.values())
tb_marg_cat = collections.Counter(v["category"] for v in tb.values())
res["task_stats_md_check"] = dict(n_rows=len(stats), n_common_with_pinned=len(st_common),
    category_disagreements_all=st_cat_dis, difficulty_disagreements_all=st_dif_dis,
    stats_table_difficulty_marginals=dict(st_marg_dif), pinned_difficulty_marginals=dict(tb_marg_dif),
    stats_table_category_marginals=dict(st_marg_cat.most_common()), pinned_category_marginals=dict(tb_marg_cat.most_common()),
    marginals_equal=(st_marg_dif == tb_marg_dif and st_marg_cat == tb_marg_cat))
json.dump(res, open(out_json, "w"), indent=1)
L.append("## Sanity check on `terminal_bench_task_stats.md` (all tasks)\n")
L.append(f"Its per-task table has {len(stats)} rows, {len(st_common)} in common with the pinned checkout; "
         f"it disagrees with the pinned task.yaml on category for {st_cat_dis} and on difficulty for {st_dif_dis} of them. "
         f"The header tables of that file (difficulty 64 easy / 120 medium / 57 hard; category counts) equal the pinned "
         f"checkout's marginals ({dict(tb_marg_dif)}), but the marginals of its own per-task table are {dict(st_marg_dif)}, "
         f"i.e. the per-task table is inconsistent with the file's own header. The per-task rows therefore do not reflect any "
         "version of the benchmark's task.yaml files and must not be used as a metadata source; the pinned task.yaml is authoritative.\n")
open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
