#!/usr/bin/env python3
"""Assemble the final census run directory for e4_analyze.py.
Usage: e4_census_merge.py <all_runs_dir> <census_runs_dir> <out_dir>
- copies every finished run file from all_runs (original E4 sample) and census_runs
- split cases (census_splits.json): rep0 evals k<=rep0_last + rep2 evals k>=rep2_kmin -> one rep0 file
- rerun cases (census_rerun_timeouts.json) with a finished rep1: rep1 replaces rep0 (rep0 had test timeouts)
"""
import json, os, sys, glob, shutil
all_dir, cen_dir, out = sys.argv[1:4]; E4 = os.path.dirname(os.path.abspath(cen_dir))
os.makedirs(out, exist_ok=True); [os.remove(f) for f in glob.glob(os.path.join(out, "*.json"))]
def finished(f):
    try: return "finished" in json.load(open(f))
    except Exception: return False
n = 0
for d in (all_dir, cen_dir):
    for f in glob.glob(os.path.join(d, "*__rep*.json")):
        if finished(f): shutil.copy(f, out); n += 1
print("copied finished files:", n)
splits = {k: v for k, v in json.load(open(os.path.join(E4, "census_splits.json"))).items() if not k.startswith("_")}
for cid, sp in splits.items():
    b, tl = sp.get("base_rep", 0), sp.get("tail_rep", 2)
    f0, f2 = os.path.join(cen_dir, f"{cid}__rep{b}.json"), os.path.join(cen_dir, f"{cid}__rep{tl}.json")
    if not (os.path.exists(f0) and finished(f2)): print("split not ready:", cid); continue
    r0, r2 = json.load(open(f0)), json.load(open(f2))
    r0["eval"] = {k: v for k, v in r0["eval"].items() if int(k) <= sp["rep0_last"]}
    r0["eval"].update({k: v for k, v in r2["eval"].items() if int(k) >= sp["rep2_kmin"]})
    # steps: rep0 steps up to rep0_last, then rep2 steps beyond (rep2 replayed 1..kmax, so take its tail)
    r0["steps"] = [s for s in r0["steps"] if s["k"] <= sp["rep0_last"]] + [s for s in r2["steps"] if s["k"] > sp["rep0_last"]]
    r0["finished"] = r2["finished"]; r0["merged_from"] = [f"rep{b}", f"rep{tl}"]; r0["rep"] = 0
    json.dump(r0, open(os.path.join(out, f"{cid}__rep0.json"), "w"), indent=1)
    for rr in (b, tl):
        p = os.path.join(out, f"{cid}__rep{rr}.json"); rr != 0 and os.path.exists(p) and os.remove(p)
    print("merged split:", cid, "evals", len(r0["eval"]))
rer = json.load(open(os.path.join(E4, "census_rerun_timeouts.json"))); swapped = kept = 0
for c in rer:
    f1 = os.path.join(out, f"{c['cid']}__rep1.json"); f0 = os.path.join(out, f"{c['cid']}__rep0.json")
    if os.path.exists(f1):
        r = json.load(open(f1)); r["rep"] = 0; r["replaced_rep0_with_timeouts"] = True
        json.dump(r, open(f0, "w"), indent=1); os.remove(f1); swapped += 1
    else: kept += 1
print(f"rerun: rep1 replaced rep0 for {swapped}; rep0 kept (no finished rerun) for {kept}")
print("final files:", len(glob.glob(os.path.join(out, "*.json"))))
