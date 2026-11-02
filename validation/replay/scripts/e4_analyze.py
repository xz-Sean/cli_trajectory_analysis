#!/usr/bin/env python3
"""Aggregate E4 replay runs.  Usage: e4_analyze.py <runs_dir> <sample.json> <pass_finals.json> <out.json>
Computes (1) rule-2 drops from faithfully replayed PASS finals, (2) per-trajectory objective lock-in (first k where
oracle-from-state fails), breach step (first MUST-NOT violation, after rule-2 filtering), progress curves (official and
MUST pass counts), agreement with human t_lock, across-rep consistency."""
import json, glob, os, sys, collections

runs_dir, sample_p, pf_p, out_p = sys.argv[1:5]
RELAX = bool(os.environ.get("E4_RELAX_BASELINE"))  # accept partial-pass oracle baselines (see below)
S = json.load(open(sample_p))
EXCL = set(json.load(open(os.path.join(os.path.dirname(sample_p), "exclusions.json")))["excluded_tasks"]) if os.path.exists(os.path.join(os.path.dirname(sample_p), "exclusions.json")) else set()
meta = {v["cid"]: v for g in ("main", "control") for v in S[g] if v["task"] not in EXCL}
pf = {c["cid"] for c in json.load(open(pf_p)) if c["cid"].split("__")[0] not in EXCL}

def load_runs():
    per = collections.defaultdict(dict)
    for f in glob.glob(os.path.join(runs_dir, "*__rep*.json")):
        r = json.load(open(f))
        if "finished" in r and not r.get("skipped"): per[r["cid"]][r["rep"]] = r
    return per
per = load_runs()

def official_ok(ev): t = ev["tests"]; return t["total"] > 0 and t["passed"] == t["total"]
def oracle_ok(ev): o = ev.get("oracle"); return bool(o and o["total"] > 0 and o["passed"] == o["total"])
def sub_failed(ev): s = ev["tests"].get("sub") or {}; return {n.split("::")[-1] for c in s.values() for n in c.get("failed_names", [])}
def sub_pass(ev, cat): s = (ev["tests"].get("sub") or {}).get(cat) or {}; return s.get("passed"), s.get("total")

# ---- rule 2: sub-tests failing on faithfully replayed PASS finals are dropped (per task)
drops = collections.defaultdict(set); pf_faithful = pf_unfaithful = 0; unfaithful_list = []
for cid in pf:
    if cid not in per: continue
    r = per[cid][min(per[cid])]; ev = r["eval"].get(str(r["m"]))
    if not ev: continue
    if official_ok(ev):
        pf_faithful += 1
        for n in sub_failed(ev): drops[cid.split("__")[0]].add(n)
    else:
        pf_unfaithful += 1; unfaithful_list.append(cid)

def filtered_counts(ev, task, cat):
    """(passed, total) for a sub-test category after removing rule-2-dropped tests"""
    s = (ev["tests"].get("sub") or {}).get(cat) or {}
    tot = s.get("total") or 0; failed = [n.split("::")[-1] for n in s.get("failed_names", [])]
    dropped_here = [n for n in failed if n in drops[task]]
    # dropped tests may also have passed; we cannot see passed names, so subtract only failed-dropped from both
    return (s.get("passed") or 0), tot - len(dropped_here), [n for n in failed if n not in drops[task]]

rows = []
for cid, reps in per.items():
    if cid not in meta: continue
    m = meta[cid]; task = m["task"]; tl, te = m["t_lock"], m["t_err"]
    summ = {}
    for rep, r in reps.items():
        ks = sorted(int(k) for k in r["eval"] if k != "0")
        recov = {k: oracle_ok(r["eval"][str(k)]) for k in ks}
        base_ok = oracle_ok(r["eval"]["0"]) if "0" in r["eval"] else None
        base_level = None
        if RELAX and base_ok is False and "0" in r["eval"]:
            # relaxed baseline: the reference solution passes only part of the official tests on today's pristine
            # image (e.g. build-cython-ext 10/11, find-official-code 1/2); recoverable(k) := oracle reaches that level
            o0 = r["eval"]["0"].get("oracle") or {}
            if (o0.get("total") or 0) > 0 and (o0.get("passed") or 0) > 0:
                base_level = (o0["passed"], o0["total"])
                def _ok(ev, lvl=base_level):
                    o = ev.get("oracle") or {}; return bool(o.get("total") == lvl[1] and (o.get("passed") or 0) >= lvl[0])
                recov = {k: _ok(r["eval"][str(k)]) for k in ks}; base_ok = True
        t_lock_obj = next((k for k in ks if not recov[k]), None)
        sticky = t_lock_obj is not None and all(not recov[k] for k in ks if k >= t_lock_obj)
        # rule 3 (replay-time): a MUST-NOT test that already fails on THIS replay's pristine snapshot (k=0) cannot be an
        # agent action (image nondeterminism / host drift, e.g. extract-elf a.out md5, configure-git-webserver sshd) -> ignored
        k0_mn = set(filtered_counts(r["eval"]["0"], task, "mustnot")[2]) if "0" in r["eval"] else set()
        def mn_at(k): return set(filtered_counts(r["eval"][str(k)], task, "mustnot")[2]) - k0_mn
        breach = None; breach_names = []
        for k in ks:
            failed = sorted(mn_at(k))
            if failed: breach = k; breach_names = failed; break
        breach_sticky = breach is not None and all(set(breach_names) & mn_at(k) for k in ks if k >= breach)
        # t_lock contradiction checks: state broken at the annotated lock-in but repaired afterwards
        last_le = [k for k in ks if k <= tl]
        state_repaired_after_lock = bool(last_le) and (not recov[last_le[-1]]) and any(recov[k] for k in ks if k > tl)
        mn_lock = mn_at(last_le[-1]) if last_le else set()
        mustnot_reverted_after_lock = bool(mn_lock) and any(not (mn_lock & mn_at(k)) for k in ks if k > tl)
        off = {k: r["eval"][str(k)]["tests"]["passed"] for k in ks}
        must = {k: filtered_counts(r["eval"][str(k)], task, "must")[0] for k in ks}
        def win(curve, lo, hi):
            v = [curve[k] for k in ks if lo <= k <= hi and curve.get(k) is not None]
            return (max(v[1:]) > v[0]) if len(v) == hi - lo + 1 else None
        off_before5, off_after5 = win(off, tl - 5, tl), win(off, tl, tl + 5)
        off_flat = len(set(v for v in off.values() if v is not None)) <= 1
        sims = [s["out_sim"] for s in r["steps"]]
        summ[rep] = dict(ks=ks, recov=recov, t_lock_obj=t_lock_obj, sticky=sticky, breach=breach, breach_names=breach_names, breach_sticky=breach_sticky,
                         k0_mustnot_excluded=sorted(k0_mn), state_repaired_after_lock=state_repaired_after_lock, mustnot_reverted_after_lock=mustnot_reverted_after_lock,
                         off=off, must=must, off_before5=off_before5, off_after5=off_after5, off_flat=off_flat,
                         base_ok=base_ok, base_level=base_level, sim=round(sum(sims)/len(sims), 3) if sims else None, timeouts=sum("E4 TIMEOUT" in s["out_tail"] for s in r["steps"]))
    objs = [x["t_lock_obj"] for x in summ.values()]; cnt = collections.Counter(objs); maj, n = cnt.most_common(1)[0]
    rel = ("never_locks_objectively" if maj is None else "agree_pm1" if abs(maj - tl) <= 1 else "human_later" if maj < tl else "human_earlier")
    r0 = summ[min(summ)]
    def prog_after(curve):
        if tl not in curve: return None
        later = [curve[k] for k in r0["ks"] if k > tl]; return (max(later) > curve[tl]) if later else None
    breaches = [x["breach"] for x in summ.values()]; br = next((b for b in breaches if b is not None), None)
    rows.append(dict(cid=cid, task=task, scaffold=m["scaffold"], why=m["why"], t_err=te, t_lock=tl, m=m["m"],
                     t_lock_obj=maj, t_lock_obj_by_rep=objs, rep_consistent=(len(summ) > 1 and n == len(summ)), relation=rel,
                     sticky=[x["sticky"] for x in summ.values()], breach=br, breach_rel=(None if br is None else "le_t_err" if br <= te else "in_window" if br <= tl else "after_lock"),
                     breach_pos=(None if br is None else "before_t_err" if br < te else "at_t_err" if br == te else "in_window" if br <= tl else "after_lock"),
                     breach_names=r0["breach_names"], breach_sticky=r0["breach_sticky"], k0_mustnot_excluded=r0["k0_mustnot_excluded"],
                     state_repaired_after_lock=r0["state_repaired_after_lock"], mustnot_reverted_after_lock=r0["mustnot_reverted_after_lock"],
                     obj_lock_before_t_err=(maj is not None and maj < te), obj_lock_before_t_err_sticky=(maj is not None and maj < te and all(x["sticky"] for x in summ.values())),
                     official_progress_before5=r0["off_before5"], official_progress_after5=r0["off_after5"], official_flat=r0["off_flat"],
                     official_progress_after_lock=prog_after(r0["off"]), must_progress_after_lock=prog_after(r0["must"]),
                     baseline_oracle_ok=r0["base_ok"], baseline_level=r0["base_level"], mean_sim=[x["sim"] for x in summ.values()], timeouts=[x["timeouts"] for x in summ.values()], n_reps=len(summ)))

valid = [r for r in rows if r["baseline_oracle_ok"] is not False]
def C(key, rs): return dict(collections.Counter(r[key] for r in rs))
summary = {
 "n_sample_traj_with_runs": len(rows), "n_valid(oracle ok on pristine)": len(valid), "excluded_baseline_oracle_fail": [r["cid"] for r in rows if r["baseline_oracle_ok"] is False],
 "rule2": {"pass_finals_faithful": pf_faithful, "pass_finals_unfaithful": pf_unfaithful, "unfaithful": unfaithful_list, "dropped_subtests": {t: sorted(v) for t, v in drops.items()}},
 "relation": C("relation", valid),
 "relation_by_tier": {w: C("relation", [r for r in valid if r["why"] == w]) for w in sorted(set(r["why"] for r in valid))},
 "relation_by_scaffold": {sc: C("relation", [r for r in valid if r["scaffold"] == sc]) for sc in ("miniswe", "terminus2")},
 "breach_rel": C("breach_rel", valid), "breach_pos": C("breach_pos", valid),
 "breach_sticky_before_t_err": [r["cid"] for r in valid if r["breach_pos"] == "before_t_err" and r["breach_sticky"]],
 "k0_mustnot_excluded": dict(collections.Counter(f"{r['task']}::{n}" for r in valid for n in r["k0_mustnot_excluded"])),
 "state_repaired_after_lock": [r["cid"] for r in valid if r["state_repaired_after_lock"]],
 "mustnot_reverted_after_lock": [r["cid"] for r in valid if r["mustnot_reverted_after_lock"]],
 "obj_lock_before_t_err": {"n": sum(r["obj_lock_before_t_err"] for r in valid), "sticky": sum(r["obj_lock_before_t_err_sticky"] for r in valid)},
 "official_progress_equal_windows": {"n": sum(1 for r in valid if r["official_progress_before5"] is not None and r["official_progress_after5"] is not None),
                                     "before5": sum(1 for r in valid if r["official_progress_before5"] and r["official_progress_after5"] is not None),
                                     "after5": sum(1 for r in valid if r["official_progress_after5"] and r["official_progress_before5"] is not None)},
 "official_flat_whole_window": sum(1 for r in valid if r["official_flat"]),
 "sticky_when_locks": sum(1 for r in valid if r["t_lock_obj"] is not None and all(r["sticky"])),
 "official_progress_after_lock": C("official_progress_after_lock", valid),
 "must_progress_after_lock": C("must_progress_after_lock", valid),
 "rep_consistent_share": (sum(r["rep_consistent"] for r in valid if r["n_reps"] > 1) / max(1, sum(1 for r in valid if r["n_reps"] > 1))),
 "n_with_3_reps": sum(1 for r in valid if r["n_reps"] >= 3), "n_with_2_reps": sum(1 for r in valid if r["n_reps"] == 2),
 "mean_fidelity": round(sum(r["mean_sim"][0] for r in valid if r["mean_sim"][0] is not None) / max(1, len(valid)), 3),
 "runs_with_step_timeouts": sum(1 for r in valid if any(r["timeouts"])),
}
json.dump({"summary": summary, "rows": rows}, open(out_p, "w"), indent=1, default=str)
print(json.dumps(summary, indent=1, default=str))
