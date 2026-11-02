#!/usr/bin/env python3 -I
"""E7 step 1: read task.yaml of every task in the pinned Terminal-Bench checkout.

Usage: python3 -I e7_task_metadata.py <original-tasks dir> <out csv>
The task files are untrusted downloaded data: only yaml.safe_load is used,
nothing is executed.
"""
import csv, os, sys, json, collections
import yaml

tasks_dir, out_csv = sys.argv[1], sys.argv[2]
rows = []
extra_keys = collections.Counter()
for name in sorted(os.listdir(tasks_dir)):
    d = os.path.join(tasks_dir, name)
    if not os.path.isdir(d):
        continue
    yp = os.path.join(d, "task.yaml")
    if not os.path.exists(yp):
        rows.append(dict(task=name, category="", difficulty="", tags="", has_task_yaml=0,
                         has_solution=int(os.path.exists(os.path.join(d, "solution.sh"))),
                         has_tests=int(os.path.isdir(os.path.join(d, "tests"))), note="no task.yaml"))
        continue
    with open(yp, encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}
    for k in y:
        extra_keys[k] += 1
    tags = y.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    rows.append(dict(
        task=name,
        category=str(y.get("category", "")).strip(),
        difficulty=str(y.get("difficulty", "")).strip(),
        difficulty_raw=repr(y.get("difficulty", "")),
        category_raw=repr(y.get("category", "")),
        tags=";".join(str(t) for t in tags),
        n_tags=len(tags),
        author_name=str(y.get("author_name", "")),
        max_agent_timeout_sec=y.get("max_agent_timeout_sec", ""),
        max_test_timeout_sec=y.get("max_test_timeout_sec", ""),
        has_task_yaml=1,
        has_solution=int(os.path.exists(os.path.join(d, "solution.sh")) or os.path.exists(os.path.join(d, "solution.yaml"))),
        has_tests=int(os.path.isdir(os.path.join(d, "tests"))),
        note="",
    ))

fields = ["task", "category", "difficulty", "tags", "n_tags", "category_raw", "difficulty_raw",
          "author_name", "max_agent_timeout_sec", "max_test_timeout_sec", "has_task_yaml",
          "has_solution", "has_tests", "note"]
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})

cats = collections.Counter(r["category"] for r in rows if r["has_task_yaml"])
diffs = collections.Counter(r["difficulty"] for r in rows if r["has_task_yaml"])
print(f"tasks: {len(rows)}  with task.yaml: {sum(r['has_task_yaml'] for r in rows)}")
print(f"task.yaml top-level keys seen: {dict(extra_keys)}")
print(f"distinct categories (raw, stripped): {len(cats)}")
for c, n in cats.most_common():
    print(f"  {c!r}: {n}")
print(f"distinct difficulty values (raw, stripped): {len(diffs)}  {dict(diffs)}")
