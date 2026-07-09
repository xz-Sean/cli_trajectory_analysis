#!/usr/bin/env python3
"""Corpus-level descriptive statistics used in the paper (dataset section + Threats to
Validity): pass/fail counts, median trajectory length, difficulty split (459/742/593),
task-category count, and the corpus-wide fabrication / silent-failure rates."""
import json, argparse, statistics as st
from collections import Counter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", default="data/traj_data_v2_all89tasks.json")
    ap.add_argument("--tasks", default="data/merged_tasks.json")
    a = ap.parse_args()
    recs = [r for r in json.load(open(a.data)) if r.get("schema_version") == "v2"]
    tasks = {t["task_id"]: t for t in json.load(open(a.tasks))}
    fail = [r for r in recs if "t_commit" in r]
    pas = [r for r in recs if "t_commit" not in r]

    print(f"trajectories: {len(recs)}  (fail {len(fail)} / pass {len(pas)})")
    print(f"tasks: {len(tasks)}   task categories: {len(set(t['category'] for t in tasks.values()))}")
    print(f"steps (m): median {st.median(r['m'] for r in recs):.0f}  "
          f"| fail median {st.median(r['m'] for r in fail):.0f} (mean {st.mean(r['m'] for r in fail):.0f})  "
          f"| pass median {st.median(r['m'] for r in pas):.0f}")

    diff = Counter(tasks.get(r["case_id"].split("__")[0], {}).get("difficulty") for r in recs)
    print("difficulty split (trajectories): " +
          "  ".join(f"{d} {diff[d]}" for d in ["easy", "medium", "hard"]))

    silent = sum(r.get("t_surface") is None for r in fail) / len(fail)
    fab = sum(r.get("fabrication_present") for r in fail) / len(fail)
    print(f"among failures: silent (no t_obs) {silent:.0%}  |  fabrication {fab:.0%}")
    # epistemic share (Table II headline)
    EPI = {"false_premise", "misread_output", "ignored_signal", "spec_neglect", "premature_action"}
    COMP = {"knowledge_gap", "capability_limit"}
    g = Counter("epistemic" if r["trigger_mechanism"] in EPI else
                "competence" if r["trigger_mechanism"] in COMP else "environment" for r in fail)
    n = len(fail)
    print(f"root cause: epistemic {g['epistemic']/n:.1%} | competence {g['competence']/n:.1%} | environment {g['environment']/n:.1%}")

if __name__ == "__main__":
    main()
