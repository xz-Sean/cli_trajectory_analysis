#!/usr/bin/env python3
"""
score_oracle.py — score detection-oracle outputs into PR curve, lead time, FP control,
and the early-stop counterfactual.

Inputs:
    oracle_sample.jsonl  (from sample_oracle.py: case_id, side, cut_step, t_commit, m, label, ...)
    oracle_calls.jsonl   (your batch output: one line per prefix with
                          {case_id, cut_step, committed: bool, confidence: float, decisive_step})

Usage:
    python3 score_oracle.py --sample oracle_sample.jsonl --calls oracle_calls.jsonl \
        --out oracle_results.json

Pure stdlib. Defines alarm = (committed AND confidence >= tau); sweeps tau.
"""
import json, argparse, statistics as st
from collections import defaultdict

def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--calls", required=True)
    ap.add_argument("--out", default="oracle_results.json")
    args = ap.parse_args()

    sample = {(r["case_id"], r["cut_step"]): r for r in load(args.sample)}
    calls = load(args.calls)
    # join
    rows = []
    for c in calls:
        key = (c["case_id"], c["cut_step"])
        if key not in sample:
            continue
        s = sample[key]
        rows.append({**s, "committed": bool(c.get("committed", False)),
                     "confidence": float(c.get("confidence", 0.0)),
                     "decisive_step": c.get("decisive_step")})
    miss = len(calls) - len(rows)
    R = {"n_calls": len(calls), "n_joined": len(rows), "n_unjoined": miss}

    taus = [i / 100 for i in range(0, 101, 2)]

    def alarm(r, tau):
        return r["committed"] and r["confidence"] >= tau

    # ---- 3a detection quality: POSITIVE vs NEGATIVE only ----
    pr = []
    pos = [r for r in rows if r["label"] == "POSITIVE"]
    neg = [r for r in rows if r["label"] == "NEGATIVE"]
    for tau in taus:
        tp = sum(1 for r in pos if alarm(r, tau))
        fn = len(pos) - tp
        fp = sum(1 for r in neg if alarm(r, tau))
        tn = len(neg) - fp
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        pr.append({"tau": tau, "precision": round(prec, 4), "recall": round(rec, 4),
                   "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn, "tn": tn})
    best = max(pr, key=lambda x: x["f1"])
    tau_star = best["tau"]
    R["pr_curve"] = pr
    R["operating_point"] = best

    # silent vs non-silent recall at tau*
    for grp, name in (([r for r in pos if r.get("silent")], "silent"),
                      ([r for r in pos if not r.get("silent")], "non_silent")):
        if grp:
            R[f"recall_{name}"] = sum(1 for r in grp if alarm(r, tau_star)) / len(grp)

    # ---- 3b lead time at tau* (per failed trajectory) ----
    by_traj = defaultdict(list)
    for r in rows:
        if r["side"] == "fail":
            by_traj[r["case_id"]].append(r)
    leads, caught, caught_before = [], 0, 0
    lead_by_trig, lead_by_tier = defaultdict(list), defaultdict(list)
    for cid, prefs in by_traj.items():
        prefs.sort(key=lambda x: x["cut_step"])
        tc = prefs[0]["t_commit"]
        fired = [p for p in prefs if alarm(p, tau_star)]
        if not fired:
            continue
        caught += 1
        t_alarm = min(p["cut_step"] for p in fired)
        lead = tc - t_alarm
        leads.append(lead)
        if lead > 0:
            caught_before += 1
        lead_by_trig[prefs[0]["trigger"]].append(lead)
        tier = "early" if tc <= 6 else "mid" if tc <= 12 else "late"
        lead_by_tier[tier].append(lead)
    R["lead_time"] = {
        "tau_star": tau_star,
        "n_failed_traj": len(by_traj),
        "caught_share": caught / len(by_traj) if by_traj else 0,
        "caught_before_commit_share": caught_before / len(by_traj) if by_traj else 0,
        "lead_median": st.median(leads) if leads else None,
        "lead_mean": round(st.mean(leads), 2) if leads else None,
        "by_trigger": {k: st.median(v) for k, v in lead_by_trig.items()},
        "by_tier": {k: st.median(v) for k, v in lead_by_tier.items()},
    }

    # ---- 3c false-positive control by prefix fraction ----
    fp_by_frac = defaultdict(lambda: [0, 0])
    for r in neg:
        frac = round(r["cut_step"] / r["m"], 1)
        fp_by_frac[frac][1] += 1
        if alarm(r, tau_star):
            fp_by_frac[frac][0] += 1
    R["fp_by_prefix_fraction"] = {str(k): round(v[0] / v[1], 4) for k, v in sorted(fp_by_frac.items())}
    R["overall_fp_rate_at_tau_star"] = sum(1 for r in neg if alarm(r, tau_star)) / len(neg) if neg else 0

    # ---- 3d early-stop counterfactual (conservative: count savings only at/after commit) ----
    es = []
    for tau in taus:
        saved = 0
        total_fail_tail = 0
        for cid, prefs in by_traj.items():
            prefs.sort(key=lambda x: x["cut_step"])
            tc = prefs[0]["t_commit"]
            m = prefs[0]["m"]
            total_fail_tail += (m - tc)
            fired = [p for p in prefs if alarm(p, tau) and p["cut_step"] >= tc]
            if fired:
                t_alarm = min(p["cut_step"] for p in fired)
                saved += max(0, m - t_alarm)
        # mis-stop cost on passes
        cut_pass = 0
        total_pass = 0
        by_pass = defaultdict(list)
        for r in neg:
            by_pass[r["case_id"]].append(r)
        for cid, prefs in by_pass.items():
            prefs.sort(key=lambda x: x["cut_step"])
            m = prefs[0]["m"]
            total_pass += m
            fired = [p for p in prefs if alarm(p, tau)]
            if fired:
                cut_pass += (m - min(p["cut_step"] for p in fired))
        save_frac = saved / total_fail_tail if total_fail_tail else 0
        cost_frac = cut_pass / total_pass if total_pass else 0
        es.append({"tau": tau, "save_frac": round(save_frac, 4),
                   "cost_frac": round(cost_frac, 4), "net": round(save_frac - cost_frac, 4)})
    R["early_stop"] = es
    R["early_stop_best"] = max(es, key=lambda x: x["net"])

    # ---- decisive_step vs annotation (independent reliability) ----
    diffs = [r["decisive_step"] - r["t_commit"] for r in rows
             if r["label"] == "POSITIVE" and isinstance(r.get("decisive_step"), int)]
    if diffs:
        R["decisive_vs_tcommit"] = {"median_diff": st.median(diffs),
                                    "within2": sum(1 for x in diffs if abs(x) <= 2) / len(diffs)}

    json.dump(R, open(args.out, "w"), indent=1, default=float)
    op = R["operating_point"]; lt = R["lead_time"]; eb = R["early_stop_best"]
    print(f"joined {len(rows)}/{len(calls)} calls")
    print(f"operating point tau*={op['tau']}: precision {op['precision']:.1%}, "
          f"recall {op['recall']:.1%}, F1 {op['f1']:.1%}")
    if "recall_silent" in R:
        print(f"  recall silent {R['recall_silent']:.1%} vs non-silent {R['recall_non_silent']:.1%}")
    print(f"lead time: caught {lt['caught_share']:.1%} of failures, "
          f"{lt['caught_before_commit_share']:.1%} before commit, median lead {lt['lead_median']} steps")
    print(f"FP rate at tau*: {R['overall_fp_rate_at_tau_star']:.1%}")
    print(f"early-stop best: tau={eb['tau']}, save {eb['save_frac']:.1%} of failure tail, "
          f"cost {eb['cost_frac']:.1%} of passing work, net {eb['net']:.1%}")
    print(f"-> {args.out}")

if __name__ == "__main__":
    main()
