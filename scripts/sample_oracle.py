#!/usr/bin/env python3
"""
sample_oracle.py — select oracle trajectories and build the prefix grid + ground truth.

Usage:
    python3 sample_oracle.py traj_data_v2_all89tasks.json \
        --n_fail 300 --n_pass 300 --seed 13 --out oracle_sample.jsonl

Produces oracle_sample.jsonl: one line per (trajectory, prefix_cut) with the ground-truth
label the scorer will use. The actual transcripts are NOT included here — sample.jsonl only
records case_id + cut step + label; your batch-builder joins these case_ids to the raw
trajectory transcripts you hold separately, then emits the oracle prompt per cut.

Ground-truth label per prefix cut at step t (trajectory with commitment step t_commit):
    failed,  t >= t_commit  -> "POSITIVE"   (already committed)
    failed,  t <  t_commit  -> "NOTYET"     (correct answer "no"; "yes" = early warning)
    passing, any t          -> "NEGATIVE"   (should never fire)
"""
import json, argparse, random
from collections import defaultdict, Counter

FRACS = (0.25, 0.50, 0.75, 1.00, 1.25)

def parse_id(cid):
    t, a, m = cid.split("__")
    return t, a, m

def cuts_fail(t_commit, m):
    pts = sorted({min(m, max(1, round(f * t_commit))) for f in FRACS})
    return pts

def cuts_pass(m):
    pts = sorted({min(m, max(1, round(f * m))) for f in FRACS})
    return pts

def stratified_fail(fail, n, seed):
    rng = random.Random(seed)
    usable = [r for r in fail if r["t_commit"] >= 4]
    # tertiles of t_commit
    tcs = sorted(r["t_commit"] for r in usable)
    q1, q2 = tcs[len(tcs) // 3], tcs[2 * len(tcs) // 3]
    def tier(r):
        return 0 if r["t_commit"] <= q1 else 1 if r["t_commit"] <= q2 else 2
    buckets = defaultdict(list)
    for r in usable:
        buckets[tier(r)].append(r)
    per = n // 3
    chosen = []
    silent_target = int(round(0.28 * n))  # match global silent rate
    for t in (0, 1, 2):
        pool = buckets[t][:]
        rng.shuffle(pool)
        # within tier, ensure trigger spread: sort so we round-robin by trigger
        bytrig = defaultdict(list)
        for r in pool:
            bytrig[r["trigger_mechanism"]].append(r)
        order, idx = [], 0
        keys = list(bytrig)
        while len(order) < len(pool):
            k = keys[idx % len(keys)]
            if bytrig[k]:
                order.append(bytrig[k].pop())
            idx += 1
            if all(not v for v in bytrig.values()):
                break
        chosen.extend(order[:per])
    # top up / enforce silent quota
    have = {r["case_id"] for r in chosen}
    silent_have = sum(1 for r in chosen if r["t_surface"] is None)
    if silent_have < silent_target:
        extra = [r for r in usable if r["t_surface"] is None and r["case_id"] not in have]
        rng.shuffle(extra)
        # swap in silent ones, replacing non-silent
        nonsilent = [r for r in chosen if r["t_surface"] is not None]
        rng.shuffle(nonsilent)
        need = silent_target - silent_have
        for s in extra[:need]:
            if nonsilent:
                drop = nonsilent.pop()
                chosen = [r for r in chosen if r["case_id"] != drop["case_id"]]
                chosen.append(s)
    return chosen[:n]

def stratified_pass(ps, n, seed, fail_tasks):
    rng = random.Random(seed + 1)
    # prefer passes whose task also has a sampled failure (same-task control)
    pref = [r for r in ps if parse_id(r["case_id"])[0] in fail_tasks]
    rest = [r for r in ps if parse_id(r["case_id"])[0] not in fail_tasks]
    rng.shuffle(pref); rng.shuffle(rest)
    return (pref + rest)[:n]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--n_fail", type=int, default=300)
    ap.add_argument("--n_pass", type=int, default=300)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default="oracle_sample.jsonl")
    args = ap.parse_args()

    data = json.load(open(args.data))
    fail = [r for r in data if "t_commit" in r]
    ps = [r for r in data if "t_commit" not in r]

    sel_fail = stratified_fail(fail, args.n_fail, args.seed)
    fail_tasks = {parse_id(r["case_id"])[0] for r in sel_fail}
    sel_pass = stratified_pass(ps, args.n_pass, args.seed, fail_tasks)

    lines = []
    for r in sel_fail:
        for t in cuts_fail(r["t_commit"], r["m"]):
            lines.append({"case_id": r["case_id"], "side": "fail", "cut_step": t,
                          "t_err": r["t_err"], "t_commit": r["t_commit"], "m": r["m"],
                          "silent": r["t_surface"] is None,
                          "trigger": r["trigger_mechanism"],
                          "label": "POSITIVE" if t >= r["t_commit"] else "NOTYET"})
    for r in sel_pass:
        for t in cuts_pass(r["m"]):
            lines.append({"case_id": r["case_id"], "side": "pass", "cut_step": t,
                          "t_commit": None, "m": r["m"], "label": "NEGATIVE"})

    with open(args.out, "w") as f:
        for ln in lines:
            f.write(json.dumps(ln) + "\n")

    # report
    lab = Counter(ln["label"] for ln in lines)
    print(f"selected: {len(sel_fail)} fail, {len(sel_pass)} pass")
    print(f"prefix cuts: {len(lines)} total -> {dict(lab)}")
    print(f"silent in fail sample: {sum(1 for r in sel_fail if r['t_surface'] is None)}/{len(sel_fail)}")
    print(f"trigger spread: {dict(Counter(r['trigger_mechanism'] for r in sel_fail))}")
    cells = Counter((parse_id(r['case_id'])[1], parse_id(r['case_id'])[2]) for r in sel_fail)
    print(f"agent x model cells covered (fail): {len(cells)}/21")
    print(f"-> {args.out}")
    print("\nNEXT: join these case_ids to your raw transcripts, truncate each to cut_step,")
    print("fill the oracle prompt (see oracle_DESIGN.md §2), and submit as a Batch job.")

if __name__ == "__main__":
    main()
