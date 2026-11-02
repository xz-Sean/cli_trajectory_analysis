#!/usr/bin/env python3
"""
rq23_analysis.py — RQ2 (failure evolution) & RQ3 (sources of variation) modules M11-M16.
Companion to rq1_analysis.py; same conventions, pure stdlib, fully reproducible.

Usage:
    python3 rq23_analysis.py <v2_annotations.json> [--boot 10000] [--vboot 2000]
                             [--outdir results/]

Outputs (in --outdir):
    results_rq23.json   every number/test/CI for RQ2-RQ3
    endings.csv         last-3-step action mix, pass vs fail        (RQ2 figure)
    regimes.csv         degradation regimes: share/cost/by-system   (RQ2 central table)
    recovery_budget.csv pass-detour vs fail-tail distributions      (RQ2 figure)
    variance_decomp.csv two-way decomposition + bootstrap CIs       (RQ3 central table)
    sensitivity.csv     per-model scaffold-sensitivity spreads      (RQ3 figure)

Modules:
    M11 behavior inversion at commit (per-trajectory paired test)
    M12 claim hygiene & trajectory endings
    M13 recovery budget (pass detours vs fail tails)
    M14 degradation regimes (awareness x tail behavior)
    M15 two-way variance decomposition with task-bootstrap CIs (+ cap check)
    M16 trigger fingerprints (Cramér's V) & awareness latency
"""
import json, sys, math, random, csv, argparse, statistics as st
from collections import Counter, defaultdict

# ---------------- shared stats (same implementations as rq1_analysis.py) ----
def wilcoxon_signed(deltas):
    d = [x for x in deltas if x != 0]
    n = len(d)
    if n < 6:
        return None, None
    ranked = sorted(range(n), key=lambda i: abs(d[i]))
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[ranked[j + 1]]) == abs(d[ranked[i]]):
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[ranked[k]] = avg
        i = j + 1
    Wp = sum(r[i] for i in range(n) if d[i] > 0)
    mu = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (Wp - mu) / sd
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return Wp, p

def boot_ci(values, stat=st.mean, n_boot=10000, alpha=0.05, seed=42):
    rng = random.Random(seed)
    n = len(values)
    sims = sorted(stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    return stat(values), sims[int(alpha / 2 * n_boot)], sims[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]

def cramers_v(table):
    """table: dict[row][col] -> count. Returns (chi2, V)."""
    rows = list(table)
    cols = sorted({c for r in table for c in table[r]})
    N = sum(sum(table[r].values()) for r in rows)
    chi2 = 0.0
    for r in rows:
        rt = sum(table[r].values())
        for c in cols:
            ct = sum(table[x].get(c, 0) for x in rows)
            exp = rt * ct / N
            if exp > 0:
                chi2 += (table[r].get(c, 0) - exp) ** 2 / exp
    k = min(len(rows), len(cols))
    return chi2, math.sqrt(chi2 / (N * (k - 1)))

# ---------------- helpers ----------------
def parse_id(cid):
    t, a, m = cid.split("__")
    return t, a, m

def expand(r):
    arr = ["O"] * r["m"]
    for s, e, c in r["action_segments"]:
        for i in range(s, e + 1):
            arr[i - 1] = c
    return arr

REGIME_RULES = [
    # (name, predicate) — first match wins; ordered by specificity
    ("fabricated_exit",   lambda r: r["tail_dominant_behavior"] == "fabrication"),
    ("quick_capitulation",lambda r: r["tail_dominant_behavior"] == "immediate_claim"),
    ("theatrical_winddown",lambda r: r["tail_dominant_behavior"] == "verification_theater"),
    ("misdiagnosed_repair",lambda r: r["awareness"] in ("aware_wrong_fix", "aware_too_late")),
    ("blind_persistence", lambda r: True),  # remainder: never_aware/aware_abandoned thrash etc.
]

def regime_of(r):
    for name, pred in REGIME_RULES:
        if pred(r):
            return name

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--vboot", type=int, default=2000,
                    help="bootstrap iterations for variance components (heavier)")
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()
    import os
    os.makedirs(args.outdir, exist_ok=True)

    data = json.load(open(args.data))
    fail = [r for r in data if "t_commit" in r]
    pas = [r for r in data if "t_commit" not in r]
    nF, nP = len(fail), len(pas)
    R = {"input": args.data, "n_fail": nF, "n_pass": nP,
         "n_boot": args.boot, "n_vboot": args.vboot}
    print(f"=== RQ2/RQ3 analysis: {nF} fail, {nP} pass ===\n")

    # ========== M11: behavior inversion at commit ==========
    # Per-trajectory paired pre/post shares -> each trajectory is its own control.
    inv = {}
    for code in "EVRWXC":
        deltas, pre_sh, post_sh = [], [], []
        for r in fail:
            arr, tc = expand(r), r["t_commit"]
            if tc >= r["m"]:          # no post-commit steps -> skip pairing
                continue
            a, b = arr[:tc], arr[tc:]
            pa, pb = a.count(code) / len(a), b.count(code) / len(b)
            deltas.append(pb - pa)
            pre_sh.append(pa)
            post_sh.append(pb)
        Wp, p = wilcoxon_signed(deltas)
        inv[code] = {"n": len(deltas),
                     "pre_mean": round(st.mean(pre_sh), 4),
                     "post_mean": round(st.mean(post_sh), 4),
                     "median_delta": round(st.median(deltas), 4),
                     "delta_CI": boot_ci(deltas, n_boot=args.boot, seed=60 + ord(code))[1:],
                     "wilcoxon_p": p,
                     "share_increasing": sum(1 for d in deltas if d > 0) / len(deltas)}
    R["M11"] = inv
    print("M11 behavior inversion (per-trajectory paired, pre -> post commit):")
    for code in "EVR":
        v = inv[code]
        print(f"   {code}: {v['pre_mean']:.1%} -> {v['post_mean']:.1%}, "
              f"median d {v['median_delta']:+.3f}, p={v['wilcoxon_p']:.2g}, "
              f"rises in {v['share_increasing']:.1%} of trajectories")
    print()

    # ========== M12: claim hygiene & endings ==========
    def hygiene(grp, k=3):
        flags = []
        for r in grp:
            arr = expand(r)
            idxs = [i for i, c in enumerate(arr) if c == "C"]
            if not idxs:
                continue
            last = idxs[-1]
            flags.append(1 if "V" in arr[max(0, last - k):last] else 0)
        return flags
    hf, hp = hygiene(fail), hygiene(pas)
    R["M12"] = {
        "fail_claims": len(hf), "pass_claims": len(hp),
        "fail_hygiene": {"share": st.mean(hf), "CI": boot_ci(hf, n_boot=args.boot, seed=70)[1:]},
        "pass_hygiene": {"share": st.mean(hp), "CI": boot_ci(hp, n_boot=args.boot, seed=71)[1:]},
        "fail_no_claim_share": (nF - len(hf)) / nF,
    }
    with open(f"{args.outdir}/endings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "code", "share_last3"])
        for name, grp in (("pass", pas), ("fail", fail)):
            c = Counter()
            for r in grp:
                arr = expand(r)
                c.update(arr[-3:] if len(arr) >= 3 else arr)
            tot = sum(c.values())
            for code in "EPWXVRCO":
                w.writerow([name, code, round(c[code] / tot, 4)])
    print(f"M12 claim hygiene (V within 3 steps before final claim): "
          f"pass {st.mean(hp):.1%} CI {R['M12']['pass_hygiene']['CI']} vs "
          f"fail {st.mean(hf):.1%} CI {R['M12']['fail_hygiene']['CI']}; "
          f"{R['M12']['fail_no_claim_share']:.1%} of fails never claim -> endings.csv\n")

    # ========== M13: recovery budget ==========
    det = [r["max_detour_length"] for r in pas if r["num_recoveries"] > 0]
    ftail = [r["m"] - r["t_commit"] for r in fail if r["num_recovery_attempts"] > 0]
    fatt = [r["num_recovery_attempts"] for r in fail if r["num_recovery_attempts"] > 0]
    qs = lambda v: {"median": st.median(v),
                    "p75": sorted(v)[int(.75 * len(v))],
                    "p90": sorted(v)[int(.9 * len(v))], "max": max(v)}
    R["M13"] = {"pass_detour_when_recovered": qs(det),
                "fail_tail_when_attempting": qs(ftail),
                "fail_attempts_when_attempting": qs(fatt),
                "pass_detour_le10_share": sum(1 for x in det if x <= 10) / len(det),
                "pass_detour_le20_share": sum(1 for x in det if x <= 20) / len(det)}
    with open(f"{args.outdir}/recovery_budget.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["steps", "pass_detour_cdf", "fail_tail_cdf"])
        for k in range(0, 61):
            w.writerow([k, sum(1 for x in det if x <= k) / len(det),
                        sum(1 for x in ftail if x <= k) / len(ftail)])
    print(f"M13 recovery budget: successful recoveries close within "
          f"{R['M13']['pass_detour_when_recovered']['median']} steps (median), "
          f"{R['M13']['pass_detour_le20_share']:.0%} within 20; failed attempts drag "
          f"median {R['M13']['fail_tail_when_attempting']['median']} steps -> recovery_budget.csv\n")

    # ========== M14: degradation regimes ==========
    rows, agg = [], defaultdict(list)
    for r in fail:
        agg[regime_of(r)].append(r)
    total_waste = sum(r["m"] - r["t_commit"] for r in fail)
    for name, grp in sorted(agg.items(), key=lambda x: -len(x[1])):
        tails = [r["m"] - r["t_commit"] for r in grp]
        rows.append({"regime": name, "n": len(grp), "share": round(len(grp) / nF, 4),
                     "median_tail": st.median(tails),
                     "waste_share": round(sum(tails) / total_waste, 4),
                     "fabrication_rate": round(st.mean([r["fabrication_present"] for r in grp]), 3),
                     "silent_rate": round(st.mean([r["t_surface"] is None for r in grp]), 3)})
    with open(f"{args.outdir}/regimes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    bysys = defaultdict(Counter)
    for r in fail:
        _, a, m = parse_id(r["case_id"])
        bysys[m][regime_of(r)] += 1
        bysys[a][regime_of(r)] += 1
    R["M14"] = {"regimes": rows,
                "by_system": {k: {kk: vv / sum(v.values()) for kk, vv in v.items()}
                              for k, v in bysys.items()}}
    print("M14 degradation regimes:")
    for row in rows:
        print(f"   {row['regime']:20s} {row['share']:6.1%}  med tail {row['median_tail']:5.1f}  "
              f"waste {row['waste_share']:5.1%}")
    print()

    # ========== M15: variance decomposition with task-bootstrap CIs ==========
    # Pre-index trajectories by task for fast resampling.
    bytask = defaultdict(list)
    for r in data:
        bytask[parse_id(r["case_id"])[0]].append(r)
    tasks = sorted(bytask)
    agents = sorted({parse_id(r["case_id"])[1] for r in data})
    models = sorted({parse_id(r["case_id"])[2] for r in data})

    def cell_metrics(records):
        """records -> {(a,m): {metric: value}}; None if a cell lacks data."""
        cells = defaultdict(lambda: {"n": 0, "pass": 0, "tails": [], "fab": 0,
                                     "silent": 0, "fw": 0})
        for r in records:
            _, a, m = parse_id(r["case_id"])
            c = cells[(a, m)]
            c["n"] += 1
            if "t_commit" not in r:
                c["pass"] += 1
            else:
                c["tails"].append(r["m"] - r["t_commit"])
                c["fab"] += r["fabrication_present"]
                c["silent"] += r["t_surface"] is None
                c["fw"] += r["forewarning_present"]
        out = {}
        for key, c in cells.items():
            nf = len(c["tails"])
            out[key] = {"pass_rate": c["pass"] / c["n"],
                        "med_tail": st.median(c["tails"]) if nf else None,
                        "fabrication_rate": c["fab"] / nf if nf else None,
                        "silent_rate": c["silent"] / nf if nf else None,
                        "forewarning_rate": c["fw"] / nf if nf else None}
        return out

    def decomp(cellvals, metric):
        Y = {}
        for a in agents:
            for m in models:
                v = cellvals.get((a, m), {}).get(metric)
                if v is None:
                    return None
                Y[(a, m)] = v
        grand = st.mean(Y.values())
        arow = {a: st.mean([Y[(a, m)] for m in models]) for a in agents}
        bcol = {m: st.mean([Y[(a, m)] for a in agents]) for m in models}
        ss_a = len(models) * sum((arow[a] - grand) ** 2 for a in agents)
        ss_b = len(agents) * sum((bcol[m] - grand) ** 2 for m in models)
        ss_t = sum((y - grand) ** 2 for y in Y.values())
        if ss_t == 0:
            return None
        return {"agent": ss_a / ss_t, "model": ss_b / ss_t,
                "interaction": (ss_t - ss_a - ss_b) / ss_t}

    METRICS = ["pass_rate", "med_tail", "fabrication_rate", "silent_rate", "forewarning_rate"]
    point = cell_metrics(data)
    rows = []
    rng = random.Random(99)
    sims = {m: {"agent": [], "model": [], "interaction": []} for m in METRICS}
    for _ in range(args.vboot):
        sample = [r for t in (tasks[rng.randrange(len(tasks))] for _ in tasks)
                  for r in bytask[t]]
        cv = cell_metrics(sample)
        for m in METRICS:
            dres = decomp(cv, m)
            if dres:
                for k in sims[m]:
                    sims[m][k].append(dres[k])
    for m in METRICS:
        d0 = decomp(point, m)
        row = {"metric": m}
        for k in ("model", "agent", "interaction"):
            s = sorted(sims[m][k])
            lo, hi = s[int(.025 * len(s))], s[int(.975 * len(s))]
            row[k] = round(d0[k], 3)
            row[f"{k}_CI"] = f"[{lo:.2f},{hi:.2f}]"
        rows.append(row)
    with open(f"{args.outdir}/variance_decomp.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    R["M15"] = {"decomposition": rows}
    print("M15 variance decomposition (model% / agent% / interaction%, task-bootstrap CIs):")
    for row in rows:
        print(f"   {row['metric']:18s} model {row['model']:.0%} {row['model_CI']}  "
              f"agent {row['agent']:.0%} {row['agent_CI']}  "
              f"inter {row['interaction']:.0%} {row['interaction_CI']}")
    # scaffold sensitivity per model + cap check
    sens = []
    for m in models:
        rates = {a: point[(a, m)]["pass_rate"] for a in agents if (a, m) in point}
        sens.append({"model": m, "min": round(min(rates.values()), 3),
                     "max": round(max(rates.values()), 3),
                     "spread": round(max(rates.values()) - min(rates.values()), 3)})
    with open(f"{args.outdir}/sensitivity.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sens[0].keys()); w.writeheader(); w.writerows(sens)
    cap = {}
    for a in agents:
        ms = [r["m"] for r in fail if parse_id(r["case_id"])[1] == a]
        cap[a] = sum(1 for x in ms if x >= 0.95 * max(ms)) / len(ms)
    R["M15"]["scaffold_sensitivity"] = sens
    R["M15"]["near_cap_share_by_agent"] = cap
    print(f"   scaffold sensitivity spreads -> sensitivity.csv; "
          f"near-cap shares {dict((k, round(v, 3)) for k, v in cap.items())}\n")

    # ========== M16: trigger fingerprints & awareness latency ==========
    tab_m, tab_a = defaultdict(Counter), defaultdict(Counter)
    for r in fail:
        _, a, m = parse_id(r["case_id"])
        tab_m[m][r["trigger_mechanism"]] += 1
        tab_a[a][r["trigger_mechanism"]] += 1
    chi_m, v_m = cramers_v(tab_m)
    chi_a, v_a = cramers_v(tab_a)
    lat = [r["first_awareness_step"] - r["t_surface"] for r in fail
           if r["t_surface"] is not None and r["first_awareness_step"] is not None
           and r["first_awareness_step"] >= r["t_surface"]]
    R["M16"] = {"model_trigger": {"chi2": round(chi_m, 1), "cramers_v": round(v_m, 3)},
                "agent_trigger": {"chi2": round(chi_a, 1), "cramers_v": round(v_a, 3)},
                "awareness_latency_after_surface": qs(lat) if lat else None,
                "n_latency": len(lat)}
    print(f"M16 fingerprints: model x trigger V={v_m:.3f}, agent x trigger V={v_a:.3f}; "
          f"awareness latency after surfacing: median "
          f"{R['M16']['awareness_latency_after_surface']['median']} steps (n={len(lat)})\n")

    json.dump(R, open(f"{args.outdir}/results_rq23.json", "w"), indent=1, default=float)
    print(f"=== done. all numbers -> {args.outdir}/results_rq23.json ===")

if __name__ == "__main__":
    main()
