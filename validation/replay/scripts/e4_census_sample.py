#!/usr/bin/env python3
"""Build a sample.json-shaped file for the census so e4_analyze.py can be reused.
Usage: e4_census_sample.py <e4_dir> <census_cases.json> <out.json>
main = original E4 sample main + every census case (t_err/t_lock/m from census_todo_raw.json); control = original control."""
import json, sys, os
e4, cases_p, out_p = sys.argv[1:4]
S = json.load(open(os.path.join(e4, "sample.json")))
raw = {r["cid"]: r for r in json.load(open(os.path.join(e4, "census_todo_raw.json")))}
have = {v["cid"] for v in S["main"]} | {v["cid"] for v in S["control"]}
added = 0; missing = []
for c in json.load(open(cases_p)):
    cid = c["cid"]
    if cid in have: continue
    r = raw.get(cid)
    if not r: missing.append(cid); continue
    S["main"].append(dict(cid=cid, task=r["task"], scaffold=r["scaffold"], model=cid.split("__")[2], m=r["m"],
                          t_err=r["t_err"], t_lock=r["t_lock"], why="census", replay_points=c.get("points"),
                          has_subtests=c.get("has_subtests"))); have.add(cid); added += 1
S["tasks"] = len({v["task"] for v in S["main"]})
json.dump(S, open(out_p, "w"), indent=1)
print(f"main={len(S['main'])} control={len(S['control'])} tasks={S['tasks']} added={added} missing={len(missing)} {missing[:5]}")
