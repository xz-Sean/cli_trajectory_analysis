#!/usr/bin/env python3
"""Contradiction-based validation summary of the annotated time points from the E4 census.
Usage: e4_validation_table.py <census_analysis.json> <runs_dir> <out.md> [<out.json>] [<subtests_dir>]

t_err and t_lock are behavioural annotations (first uncorrected error / last point after which no correction is
attempted).  Replay evidence can therefore CONTRADICT them only in specific ways:
  t_err  : an uncorrected objective error already exists BEFORE t_err
           (a) reference solution fails at the first snapshot (t_err-1) and never passes again in the window
           (b) a forbidden-action (MUST-NOT) sub-test first fails before t_err and stays failed
  t_lock : the agent REPAIRS the state AFTER t_lock
           (a) reference solution fails at the last snapshot <= t_lock and passes at a later one
           (b) a forbidden-action violation present at t_lock is absent at a later snapshot
Everything else (state still solvable, forbidden actions at/after t_err, no progress after t_lock) is consistent.
"""
import json, sys, os, collections, statistics
A = json.load(open(sys.argv[1])); runs = sys.argv[2]; out_md = sys.argv[3]; out_js = sys.argv[4] if len(sys.argv) > 4 else None
V = [r for r in A["rows"] if r.get("baseline_oracle_ok") is not False]
SUBDIR = sys.argv[5] if len(sys.argv) > 5 else next((d for d in (os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "subtests"), os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "..", "subtests")) if os.path.isdir(d)), None)
if SUBDIR is None: sys.exit("sub-tests directory not found; pass it as 5th argument")
n = len(V); sub = [r for r in V if r["breach_names"] is not None and r["task"] in set(os.listdir(SUBDIR))]
def pct(a, b): return f"{a}/{b} ({100*a/b:.1f}%)" if b else "–"

# ---- t_err contradictions
te_a = [r["cid"] for r in V if r["obj_lock_before_t_err_sticky"]]
te_a_any = [r["cid"] for r in V if r["obj_lock_before_t_err"]]
te_b = [r["cid"] for r in V if r["breach_pos"] == "before_t_err" and r["breach_sticky"]]
te_b_any = [r["cid"] for r in V if r["breach_pos"] == "before_t_err"]
te_union = sorted(set(te_a) | set(te_b))
# ---- t_lock contradictions
tl_a = [r["cid"] for r in V if r["state_repaired_after_lock"]]
tl_b = [r["cid"] for r in V if r["mustnot_reverted_after_lock"]]
tl_union = sorted(set(tl_a) | set(tl_b))
# ---- consistency / characterisation
locks = [r for r in V if r["t_lock_obj"] is not None]; sticky = [r for r in locks if all(r["sticky"])]
pos = collections.Counter("before_t_err" if r["t_lock_obj"] < r["t_err"] else "at_t_err" if r["t_lock_obj"] == r["t_err"] else "in_window" if r["t_lock_obj"] <= r["t_lock"] else "after_lock" for r in locks)
inside = [r for r in locks if r["t_err"] < r["t_lock_obj"] <= r["t_lock"]]
gap = [r["t_lock"] - r["t_lock_obj"] for r in inside]
prog = collections.Counter(r["official_progress_after_lock"] for r in V)
eq = A["summary"]["official_progress_equal_windows"]
bpos = collections.Counter(r["breach_pos"] for r in V if r["breach_pos"])
# per-step official increase rate around t_lock (rep0 files)
ib = nb = ia = na = 0
for r in V:
    f = os.path.join(runs, f"{r['cid']}__rep0.json")
    if not os.path.exists(f): continue
    ev = {int(k): v for k, v in json.load(open(f))["eval"].items()}; ks = sorted(k for k in ev if k > 0); tl = r["t_lock"]; prev = None
    for k in ks:
        p = (ev[k].get("tests") or {}).get("passed")
        if p is None: prev = None; continue
        if prev is not None:
            if tl - 5 < k <= tl: nb += 1; ib += p > prev
            elif tl < k <= tl + 5: na += 1; ia += p > prev
        prev = p
by_sc = {sc: [r for r in V if r["scaffold"] == sc] for sc in ("miniswe", "terminus2")}

L = []
L += ["# Validation of the annotated time points by replay (contradiction-based)", "",
      f"Source: `{os.path.basename(sys.argv[1])}`; {n} valid trajectories ({len(sub)} with calibrated sub-tests).", "",
      "t_err and t_lock are behavioural annotations. The replay can contradict them only in the ways listed; all other outcomes are consistent.", "",
      "## A. Can the replay contradict the annotation?", "",
      "| Time point | Contradiction looked for | Found | Rate |", "|---|---|---|---|",
      f"| t_err | reference solution already fails at t_err−1 and never passes again | {len(te_a)} (of {len(te_a_any)} that fail at t_err−1 at all) | {pct(len(te_a), n)} |",
      f"| t_err | forbidden action already present before t_err and never reverted | {len(te_b)} (of {len(te_b_any)} before t_err at all) | {pct(len(te_b), len(sub))} |",
      f"| t_err | **either** | {len(te_union)} | **{pct(len(te_union), n)}** |",
      f"| t_lock | state unsolvable at t_lock but solvable at a later step | {len(tl_a)} | {pct(len(tl_a), n)} |",
      f"| t_lock | forbidden action present at t_lock but reverted later | {len(tl_b)} | {pct(len(tl_b), len(sub))} |",
      f"| t_lock | **either** | {len(tl_union)} | **{pct(len(tl_union), n)}** |", "",
      f"t_err not contradicted: {pct(n-len(te_union), n)}. t_lock not contradicted: {pct(n-len(tl_union), n)}.", "",
      "Cases (to review individually):", f"- t_err / reference solution: {', '.join(te_a)}", f"- t_err / forbidden action: {', '.join(te_b)}",
      f"- t_lock / state repaired: {', '.join(tl_a)}", f"- t_lock / violation reverted: {', '.join(tl_b)}", "",
      "## B. One-sided consistency evidence", "",
      "| Expectation if annotations are right | Observation |", "|---|---|",
      f"| No task progress after t_lock | official pass count rises after t_lock in {pct(prog[True], prog[True]+prog[False])}; equal 5-step windows (n={eq['n']}): before t_lock {eq['before5']}, after {eq['after5']}; per-step rise rate {100*ib/nb:.1f}% in the 5 steps before vs {100*ia/na:.1f}% in the 5 after; pass count constant through the whole window in {A['summary']['official_flat_whole_window']} |",
      f"| Forbidden actions start at or after t_err | first forbidden action ({len(sub)} traj. with sub-tests): before t_err {bpos['before_t_err']} (sticky {len(te_b)}), at t_err {bpos['at_t_err']}, inside (t_err, t_lock] {bpos['in_window']}, after t_lock {bpos['after_lock']}, none {len(sub)-sum(bpos.values())} |",
      f"| State damage, when it happens, starts at or after t_err | reference solution fails at some step in {len(locks)} trajectories ({len(sticky)} never pass again): before t_err {pos['before_t_err']}, at t_err {pos['at_t_err']}, inside (t_err, t_lock] {pos['in_window']}, after t_lock {pos['after_lock']} |",
      f"| Annotators do not call lock-in early | of the {len(inside)} locks inside (t_err, t_lock], human t_lock is later than the objective break by a median of {statistics.median(gap) if gap else '–'} steps; objective break more than 1 step after human t_lock in {A['summary']['relation'].get('human_earlier',0)} |", "",
      "## C. What lock-in is (characterisation, not validation)", "",
      f"- Reference solution passes at every snapshot from t_err−1 to t_lock+5 in {pct(len(V)-len(locks), n)} → lock-in is a behavioural commitment while the task is still solvable.",
      f"- By scaffold: " + ", ".join(f"{sc} {pct(sum(1 for r in rs if r['t_lock_obj'] is None), len(rs))}" for sc, rs in by_sc.items()) + ".", "",
      "## D. Rules applied to the sub-tests", "",
      "- rule 1 (calibration): reference solution passes all MUST/UNTESTED and violates no MUST-NOT; rule 3 (calibration): every MUST fails on the pristine image.",
      f"- rule 2 (replay): sub-tests failing on faithfully replayed same-task PASS finals are dropped per task: {A['summary']['rule2']['dropped_subtests']}.",
      f"- rule 3' (replay, per trajectory): a MUST-NOT test already failing on this replay's pristine snapshot is ignored: {A['summary']['k0_mustnot_excluded']}.", ""]
open(out_md, "w").write("\n".join(L))
if out_js: json.dump(dict(n=n, n_sub=len(sub), t_err=dict(oracle_sticky=te_a, oracle_any=te_a_any, mustnot_sticky=te_b, mustnot_any=te_b_any, union=te_union), t_lock=dict(state_repaired=tl_a, mustnot_reverted=tl_b, union=tl_union), lock_pos=dict(pos), breach_pos=dict(bpos), n_locks=len(locks), n_sticky=len(sticky), inside_gap_median=(statistics.median(gap) if gap else None), progress_after_lock=dict(prog), equal_windows=eq, per_step=dict(before=[ib, nb], after=[ia, na]), flat=A['summary']['official_flat_whole_window']), open(out_js, "w"), indent=1, default=str)
print("\n".join(L))
