#!/usr/bin/env python3
"""
rq1_analysis.py — Full reproducible RQ1 analysis pipeline.

Usage:
    python3 rq1_analysis.py <v2_annotations.json> [--v1 <v1_annotations.json>]
                            [--boot 10000] [--outdir results/]

Outputs (in --outdir):
    results_rq1.json   every number, test statistic, and CI used in the paper
    hazard.csv         per-step commitment hazard (figure: hazard curve)
    tiers.csv          observability tier composition (figure: stacked bar)
    behavior_mix.csv   first-8-step action mix, pass vs fail (figure: grouped bar)
    paired_tasks.csv   per-task pass-fail deltas for the within-task analysis
    + a full printed report on stdout

Pure stdlib — no numpy/scipy required. All tests implemented explicitly:
    Mann-Whitney U (normal approx, tie-corrected), Cliff's delta (from U),
    exact binomial sign test, Wilcoxon signed-rank (normal approx),
    percentile bootstrap CIs.
"""
import json, sys, math, random, csv, argparse, statistics as st
from collections import Counter, defaultdict

# ---------------------------------------------------------------- stats utils
def mann_whitney(a, b):
    """Two-sided Mann-Whitney U via rank sums (tie-corrected normal approx).
    Returns (U_a, p). U_a counts pairs where a > b (+ half ties)."""
    n1, n2 = len(a), len(b)
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i = {}, 0
    vals = [v for v, _ in allv]
    # average ranks for ties
    r = [0.0] * len(vals)
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1] == vals[i]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[k] = avg
        i = j + 1
    R1 = sum(r[k] for k in range(len(allv)) if allv[k][1] == 0)
    U1 = R1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    tie_counts = Counter(vals).values()
    tie_term = sum(t**3 - t for t in tie_counts)
    var = n1 * n2 / 12 * ((n1 + n2 + 1) - tie_term / ((n1 + n2) * (n1 + n2 - 1)))
    if var <= 0:
        return U1, 1.0
    z = (U1 - mu) / math.sqrt(var)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return U1, p

def cliffs_delta(a, b):
    """P(a>b) - P(a<b), computed from Mann-Whitney U. Range [-1, 1]."""
    U1, _ = mann_whitney(a, b)
    return 2 * U1 / (len(a) * len(b)) - 1

def boot_ci(values, stat=st.mean, n_boot=10000, alpha=0.05, seed=42):
    """Percentile bootstrap CI for stat(values)."""
    rng = random.Random(seed)
    n = len(values)
    sims = sorted(stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    lo = sims[int(alpha / 2 * n_boot)]
    hi = sims[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return stat(values), lo, hi

def sign_test(deltas):
    """Exact two-sided binomial sign test on nonzero deltas."""
    pos = sum(1 for d in deltas if d > 0)
    neg = sum(1 for d in deltas if d < 0)
    n = pos + neg
    if n == 0:
        return pos, neg, 1.0
    k = min(pos, neg)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2**n * 2
    return pos, neg, min(1.0, p)

def wilcoxon_signed(deltas):
    """Wilcoxon signed-rank, two-sided, normal approximation (ties dropped)."""
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

# ---------------------------------------------------------------- helpers
EPI = {"false_premise", "misread_output", "ignored_signal", "spec_neglect", "premature_action"}
COMP = {"knowledge_gap", "capability_limit"}

def parse_id(cid):
    t, a, m = cid.split("__")
    return t, a, m

def expand(r):
    arr = ["O"] * r["m"]
    for s, e, c in r["action_segments"]:
        for i in range(s, e + 1):
            arr[i - 1] = c
    return arr

def share(r, code, upto=None):
    arr = expand(r)
    if upto:
        arr = arr[:upto]
    return arr.count(code) / len(arr)

def pct(x, n):
    return f"{x}/{n} = {x/n:.1%}"

# ---------------------------------------------------------------- analysis
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--v1", default=None)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()
    import os
    os.makedirs(args.outdir, exist_ok=True)

    data = json.load(open(args.data))
    fail = [r for r in data if "t_commit" in r]
    pas = [r for r in data if "t_commit" not in r]
    nF, nP = len(fail), len(pas)
    R = {"input": args.data, "n_fail": nF, "n_pass": nP, "n_boot": args.boot}
    print(f"=== RQ1 analysis: {nF} fail, {nP} pass, bootstrap={args.boot} ===\n")

    # ---------- M1: timepoint geometry ----------
    terr = [r["t_err"] for r in fail]
    tcom = [r["t_commit"] for r in fail]
    clag = [r["t_commit"] - r["t_err"] for r in fail]
    silent = [r for r in fail if r["t_surface"] is None]
    slag = [r["t_surface"] - r["t_commit"] for r in fail if r["t_surface"] is not None]
    pre_commit_surface = sum(1 for x in slag if x < 0)
    R["M1"] = {
        "t_err": {"median": st.median(terr), "mean": round(st.mean(terr), 2)},
        "t_commit": {"median": st.median(tcom), "mean": round(st.mean(tcom), 2)},
        "commitment_lag": {
            "median": st.median(clag), "mean": round(st.mean(clag), 2),
            "lag0": sum(1 for x in clag if x == 0),
            "lag_ge1_share": sum(1 for x in clag if x >= 1) / nF,
            "lag_ge1_CI": boot_ci([1 if x >= 1 else 0 for x in clag], n_boot=args.boot)[1:],
            "lag_ge3_share": sum(1 for x in clag if x >= 3) / nF,
            "lag_ge3_CI": boot_ci([1 if x >= 3 else 0 for x in clag], n_boot=args.boot, seed=43)[1:],
        },
        "silent_share": len(silent) / nF,
        "silent_CI": boot_ci([1 if r["t_surface"] is None else 0 for r in fail], n_boot=args.boot, seed=44)[1:],
        "surface_before_commit": pre_commit_surface,
        "cumulative_commit": {f"by_step_{t}": sum(1 for x in tcom if x <= t) / nF for t in (5, 10, 20)},
    }
    m1 = R["M1"]
    print(f"M1 timepoints: t_err med {m1['t_err']['median']}, t_commit med {m1['t_commit']['median']}")
    print(f"   lag>=1 {m1['commitment_lag']['lag_ge1_share']:.1%} CI {m1['commitment_lag']['lag_ge1_CI']}, "
          f"lag>=3 {m1['commitment_lag']['lag_ge3_share']:.1%}")
    print(f"   silent {m1['silent_share']:.1%} CI {m1['silent_CI']}; "
          f"failure visible BEFORE commit in {pre_commit_surface} cases\n")

    # ---------- M2: hazard curve ----------
    rows = []
    maxstep = max(tcom)
    for t in range(1, min(maxstep, 60) + 1):
        at_risk = sum(1 for x in tcom if x >= t)
        events = sum(1 for x in tcom if x == t)
        rows.append({"step": t, "at_risk": at_risk, "events": events,
                     "hazard": round(events / at_risk, 4) if at_risk else 0})
    with open(f"{args.outdir}/hazard.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    peak = max(rows[:20], key=lambda r: r["hazard"])
    R["M2"] = {"peak_step": peak["step"], "peak_hazard": peak["hazard"], "csv": "hazard.csv"}
    print(f"M2 hazard: peak {peak['hazard']:.3f} at step {peak['step']} -> hazard.csv\n")

    # ---------- M3: triggers ----------
    trig = Counter(r["trigger_mechanism"] for r in fail)
    grp = Counter("epistemic" if r["trigger_mechanism"] in EPI else
                  "competence" if r["trigger_mechanism"] in COMP else "env_other" for r in fail)
    epi_flag = [1 if r["trigger_mechanism"] in EPI else 0 for r in fail]
    R["M3"] = {"distribution": dict(trig.most_common()),
               "groups": {k: v / nF for k, v in grp.items()},
               "epistemic_CI": boot_ci(epi_flag, n_boot=args.boot, seed=45)[1:],
               "per_trigger_timing": {k: {"n": len(v), "med_t_err": st.median([r["t_err"] for r in v]),
                                          "med_lag": st.median([r["t_commit"] - r["t_err"] for r in v])}
                                      for k, v in [(k, [r for r in fail if r["trigger_mechanism"] == k])
                                                   for k in trig]}}
    print(f"M3 triggers: epistemic {grp['epistemic']/nF:.1%} CI {R['M3']['epistemic_CI']}, "
          f"competence {grp['competence']/nF:.1%}\n")

    # ---------- M4: forewarning & observability tiers ----------
    fw = [r for r in fail if r["forewarning_present"]]
    lead = [r["t_commit"] - r["forewarning_first_step"] for r in fw]
    lag_of = lambda r: r["t_commit"] - r["t_err"]
    tierA = [r for r in fail if r["forewarning_present"] or lag_of(r) >= 3]
    tierC = [r for r in fail if r["t_surface"] is None and lag_of(r) == 0 and not r["forewarning_present"]]
    R["M4"] = {"forewarning_share": len(fw) / nF,
               "forewarning_CI": boot_ci([1 if r["forewarning_present"] else 0 for r in fail],
                                         n_boot=args.boot, seed=46)[1:],
               "lead_median": st.median(lead), "lead_mean": round(st.mean(lead), 2),
               "tierA_share": len(tierA) / nF, "tierC_share": len(tierC) / nF,
               "tierA_CI": boot_ci([1 if (r["forewarning_present"] or lag_of(r) >= 3) else 0 for r in fail],
                                   n_boot=args.boot, seed=47)[1:]}
    with open(f"{args.outdir}/tiers.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["tier", "count", "share"])
        w.writerow(["A_observable_window", len(tierA), len(tierA) / nF])
        w.writerow(["B_intermediate", nF - len(tierA) - len(tierC), (nF - len(tierA) - len(tierC)) / nF])
        w.writerow(["C_invisible", len(tierC), len(tierC) / nF])
    print(f"M4 observability: forewarning {len(fw)/nF:.1%} (lead med {st.median(lead)}), "
          f"TierA {len(tierA)/nF:.1%}, TierC {len(tierC)/nF:.1%} -> tiers.csv\n")

    # ---------- M5: verification asymmetry & behavior mix ----------
    f_verif = [1 if (r["verification_ever"] and r["first_relevant_verification_step"] is not None
                     and r["first_relevant_verification_step"] <= r["t_commit"]) else 0 for r in fail]
    p_verif = [1 if r["verification_before_claim"] else 0 for r in pas]
    f_E8 = [share(r, "E", min(8, r["m"])) for r in fail]
    p_E8 = [share(r, "E", min(8, r["m"])) for r in pas]
    f_V8 = [share(r, "V", min(8, r["m"])) for r in fail]
    p_V8 = [share(r, "V", min(8, r["m"])) for r in pas]
    R["M5"] = {
        "fail_verified_before_commit": {"share": st.mean(f_verif),
                                        "CI": boot_ci(f_verif, n_boot=args.boot, seed=48)[1:]},
        "pass_verified_before_claim": {"share": st.mean(p_verif),
                                       "CI": boot_ci(p_verif, n_boot=args.boot, seed=49)[1:]},
        "E_share_first8": {"fail": round(st.mean(f_E8), 4), "pass": round(st.mean(p_E8), 4),
                           "cliffs_delta": round(cliffs_delta(f_E8, p_E8), 3),
                           "mw_p": mann_whitney(f_E8, p_E8)[1]},
        "V_share_first8": {"fail": round(st.mean(f_V8), 4), "pass": round(st.mean(p_V8), 4),
                           "cliffs_delta": round(cliffs_delta(f_V8, p_V8), 3),
                           "mw_p": mann_whitney(f_V8, p_V8)[1]},
    }
    with open(f"{args.outdir}/behavior_mix.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["group", "code", "share_first8"])
        for name, grp_ in (("pass", pas), ("fail", fail)):
            c = Counter()
            for r in grp_:
                c.update(expand(r)[:8])
            tot = sum(c.values())
            for code in "EPWXVRCO":
                w.writerow([name, code, round(c[code] / tot, 4)])
    m5 = R["M5"]
    print(f"M5 verification asymmetry: pass {st.mean(p_verif):.1%} CI {m5['pass_verified_before_claim']['CI']} "
          f"vs fail {st.mean(f_verif):.1%} CI {m5['fail_verified_before_commit']['CI']}")
    print(f"   first-8 E: fail {st.mean(f_E8):.1%} vs pass {st.mean(p_E8):.1%} "
          f"(delta {m5['E_share_first8']['cliffs_delta']}, p={m5['E_share_first8']['mw_p']:.2g})")
    print(f"   first-8 V: fail {st.mean(f_V8):.1%} vs pass {st.mean(p_V8):.1%} "
          f"(delta {m5['V_share_first8']['cliffs_delta']}, p={m5['V_share_first8']['mw_p']:.2g}) -> behavior_mix.csv\n")

    # ---------- M6: pass-side & post-commit dynamics ----------
    err_pass = [r for r in pas if r["num_error_events"] > 0]
    tot_err = sum(r["num_error_events"] for r in pas)
    tot_rec = sum(r["num_recoveries"] for r in pas)
    aw = Counter(r["awareness"] for r in fail)
    tail_by_aw = {k: st.median([r["m"] - r["t_commit"] for r in fail if r["awareness"] == k]) for k in aw}
    fab = [r for r in fail if r["fabrication_present"]]
    fab_after = sum(1 for r in fab if r["fabrication_onset_step"] >= r["t_commit"])
    R["M6"] = {
        "pass_with_errors_share": len(err_pass) / nP,
        "pass_error_recovery_rate": tot_rec / tot_err if tot_err else None,
        "fail_zero_recovery_share": sum(1 for r in fail if r["num_recovery_attempts"] == 0) / nF,
        "suspicious_pass_share": sum(1 for r in pas if r["suspicious_pass"]) / nP,
        "suspicious_pass_CI": boot_ci([1 if r["suspicious_pass"] else 0 for r in pas],
                                      n_boot=args.boot, seed=50)[1:],
        "near_miss_share": sum(1 for r in pas if r["near_miss"]) / nP,
        "awareness": {k: v / nF for k, v in aw.items()},
        "median_tail_by_awareness": tail_by_aw,
        "total_post_commit_steps": sum(r["m"] - r["t_commit"] for r in fail),
        "fabrication_share": len(fab) / nF,
        "fabrication_onset_at_or_after_commit": fab_after / len(fab) if fab else None,
        "tail_behavior": dict(Counter(r["tail_dominant_behavior"] for r in fail).most_common()),
    }
    print(f"M6 pass-side: {len(err_pass)/nP:.1%} of passes hit errors, recovery rate "
          f"{tot_rec/tot_err:.1%}; suspicious {R['M6']['suspicious_pass_share']:.1%}")
    print(f"   awareness: {dict(aw)}; tail med by awareness {tail_by_aw}")
    print(f"   fabrication {len(fab)/nF:.1%}, onset >= commit {fab_after/len(fab):.1%}\n")

    # ---------- M7: within-task paired analysis ----------
    bytask = defaultdict(lambda: {"p": [], "f": []})
    for r in pas:
        bytask[parse_id(r["case_id"])[0]]["p"].append(r)
    for r in fail:
        bytask[parse_id(r["case_id"])[0]]["f"].append(r)
    mixed = {t: v for t, v in bytask.items() if v["p"] and v["f"]}
    allfail_tasks = [t for t, v in bytask.items() if not v["p"]]
    paired_rows, dV, dE, dverif = [], [], [], []
    for t, v in sorted(mixed.items()):
        pV = st.mean([share(r, "V", min(8, r["m"])) for r in v["p"]])
        fV = st.mean([share(r, "V", min(8, r["m"])) for r in v["f"]])
        pE = st.mean([share(r, "E", min(8, r["m"])) for r in v["p"]])
        fE = st.mean([share(r, "E", min(8, r["m"])) for r in v["f"]])
        pvr = st.mean([1 if r["verification_before_claim"] else 0 for r in v["p"]])
        fvr = st.mean([1 if (r["verification_ever"] and r["first_relevant_verification_step"] is not None
                             and r["first_relevant_verification_step"] <= r["t_commit"]) else 0 for r in v["f"]])
        dV.append(pV - fV); dE.append(pE - fE); dverif.append(pvr - fvr)
        paired_rows.append({"task": t, "n_pass": len(v["p"]), "n_fail": len(v["f"]),
                            "dV8": round(pV - fV, 4), "dE8": round(pE - fE, 4),
                            "d_verif": round(pvr - fvr, 4)})
    with open(f"{args.outdir}/paired_tasks.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=paired_rows[0].keys()); w.writeheader(); w.writerows(paired_rows)
    res = {}
    for name, deltas in (("V_share_first8", dV), ("E_share_first8", dE), ("verification_rate", dverif)):
        pos, neg, p_sign = sign_test(deltas)
        Wp, p_wil = wilcoxon_signed(deltas)
        res[name] = {"n_tasks": len(deltas), "tasks_pass_higher": pos, "tasks_fail_higher": neg,
                     "median_delta": st.median(deltas), "sign_p": p_sign, "wilcoxon_p": p_wil}
    R["M7"] = {"n_mixed_tasks": len(mixed), "n_allfail_tasks": len(allfail_tasks), "paired": res}
    print(f"M7 within-task ({len(mixed)} mixed tasks):")
    for k, v in res.items():
        print(f"   {k}: pass higher in {v['tasks_pass_higher']}/{v['n_tasks']} tasks, "
              f"median delta {v['median_delta']:+.3f}, sign p={v['sign_p']:.2g}, "
              f"wilcoxon p={v['wilcoxon_p']:.2g}")
    print()

    # ---------- M8: sensitivity excluding all-fail tasks ----------
    keep = [r for r in fail if parse_id(r["case_id"])[0] not in set(allfail_tasks)]
    kn = len(keep)
    R["M8"] = {"n_kept": kn,
               "epistemic_share": sum(1 for r in keep if r["trigger_mechanism"] in EPI) / kn,
               "lag_ge1_share": sum(1 for r in keep if r["t_commit"] - r["t_err"] >= 1) / kn,
               "silent_share": sum(1 for r in keep if r["t_surface"] is None) / kn,
               "tierA_share": sum(1 for r in keep if r["forewarning_present"]
                                  or r["t_commit"] - r["t_err"] >= 3) / kn,
               "verif_before_commit": sum(1 for r in keep if r["verification_ever"]
                                          and r["first_relevant_verification_step"] is not None
                                          and r["first_relevant_verification_step"] <= r["t_commit"]) / kn}
    print(f"M8 sensitivity (excl. {len(allfail_tasks)} all-fail tasks, n={kn}): "
          f"epistemic {R['M8']['epistemic_share']:.1%}, lag>=1 {R['M8']['lag_ge1_share']:.1%}, "
          f"silent {R['M8']['silent_share']:.1%}, TierA {R['M8']['tierA_share']:.1%}\n")

    # ---------- M9: per system ----------
    def sysstats(keyfn):
        out = {}
        g = defaultdict(list)
        for r in fail:
            g[keyfn(r)].append(r)
        for k, v in sorted(g.items()):
            out[k] = {"n": len(v), "med_t_commit": st.median([r["t_commit"] for r in v]),
                      "med_lag": st.median([r["t_commit"] - r["t_err"] for r in v]),
                      "silent": sum(1 for r in v if r["t_surface"] is None) / len(v),
                      "fabrication": sum(1 for r in v if r["fabrication_present"]) / len(v)}
        return out
    R["M9"] = {"by_model": sysstats(lambda r: parse_id(r["case_id"])[2]),
               "by_agent": sysstats(lambda r: parse_id(r["case_id"])[1])}
    print("M9 per-system written to results json\n")

    # ---------- M10: v1 comparison ----------
    if args.v1:
        old = json.load(open(args.v1))
        oldmap = {r["case_id"]: r["command_index_ratio"]["n"] for r in old if "command_index_ratio" in r}
        de = [oldmap[r["case_id"]] - r["t_err"] for r in fail if r["case_id"] in oldmap]
        dc = [oldmap[r["case_id"]] - r["t_commit"] for r in fail if r["case_id"] in oldmap]
        R["M10"] = {"matched": len(de),
                    "old_n_vs_t_err": {"median_diff": st.median(de),
                                       "within2": sum(1 for x in de if abs(x) <= 2) / len(de)},
                    "old_n_vs_t_commit": {"median_diff": st.median(dc),
                                          "within2": sum(1 for x in dc if abs(x) <= 2) / len(dc)}}
        print(f"M10 v1 comparison: matched {len(de)}, old n within2 of t_err "
              f"{R['M10']['old_n_vs_t_err']['within2']:.1%}, of t_commit "
              f"{R['M10']['old_n_vs_t_commit']['within2']:.1%}\n")

    json.dump(R, open(f"{args.outdir}/results_rq1.json", "w"), indent=1, default=float)
    print(f"=== done. all numbers -> {args.outdir}/results_rq1.json ===")

if __name__ == "__main__":
    main()
