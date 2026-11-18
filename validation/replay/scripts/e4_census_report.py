#!/usr/bin/env python3
"""Render resub/e4/CENSUS_REPORT.md from the census analysis (run after e4_census_merge.py + e4_analyze.py).
Usage: e4_census_report.py <census_analysis.json> <pilot_analysis.json> [<inputs_dir>]  (writes CENSUS_REPORT.md next to the first file)"""
import json, sys, collections, datetime, statistics as st, os
R = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(os.path.abspath(sys.argv[1]))  # dir holding census_tasks/cases/splits/rerun json
OUT_DIR = os.path.dirname(os.path.abspath(sys.argv[1]))
A = json.load(open(sys.argv[1])); S = A["summary"]; O = json.load(open(sys.argv[2]))["summary"]
rows = [r for r in A["rows"] if r["baseline_oracle_ok"] is not False]
orig_all = [r for r in A["rows"] if r["why"] != "census"]
cen = [r for r in rows if r["why"] == "census"]; orig = [r for r in rows if r["why"] != "census"]
tasks = json.load(open(f"{R}/census_tasks.json")); cases = json.load(open(f"{R}/census_cases.json")) if os.path.exists(f"{R}/census_cases.json") else []
splits = json.load(open(f"{R}/census_splits.json")); rerun = json.load(open(f"{R}/census_rerun_timeouts.json"))
pool = sum(v.get("n_traj", 0) for v in tasks.values()); exc = {t: v for t, v in tasks.items() if v["status"] == "excluded"}
ready = {t: v for t, v in tasks.items() if v["status"] != "excluded"}
reason_groups = collections.defaultdict(lambda: [0, 0])
for t, v in exc.items():
    rs_ = v["reason"]
    key = ("reference solution fails the official tests on today's rebuilt image" if "reference solution fails" in rs_ else
           "state cannot be snapshotted faithfully (docker commit loses it)" if any(w in rs_ for w in ("commit", "ENTRYPOINT", "xattr")) else
           "prohibitive per-snapshot cost" if any(w in rs_ for w in ("cost", "prohibitive", "hours", "exceeds", ">20 h")) else
           "image cannot be rebuilt / oracle cannot run today (dependency drift, dead downloads)")
    reason_groups[key][0] += 1; reason_groups[key][1] += v.get("n_traj", 0)
def pct(a, b): return f"{a} ({100*a/b:.1f}%)" if b else "–"
def rel(rs): return collections.Counter(r["relation"] for r in rs)
def block(name, rs):
    c = rel(rs); n = len(rs); locks = [r for r in rs if r["t_lock_obj"] is not None]
    d = [r["t_lock_obj"] - r["t_lock"] for r in locks]
    br = collections.Counter(str(r["breach_rel"]) for r in rs)
    po = collections.Counter(str(r["official_progress_after_lock"]) for r in rs)
    fid = [r["mean_sim"][0] for r in rs if r["mean_sim"] and r["mean_sim"][0] is not None]
    return [f"| {name} | {n} | {pct(c['never_locks_objectively'], n)} | {len(locks)} | {sum(abs(x)<=1 for x in d)} | {sum(abs(x)<=3 for x in d)} | {sum(x<0 for x in d)} | {sum(x>1 for x in d)} | {sum(r['t_lock_obj']>=r['t_err'] for r in locks)} | {sum(all(r['sticky']) for r in locks)} | {n-br['None']} | {po['True']}/{po['True']+po['False']} | {st.median(fid):.2f} |"]
hdr = ["| group | n valid | never objectively locks | objective locks | obj within ±1 of human t_lock | within ±3 | obj earlier than human (>1) | obj later than human (>1) | obj lock ≥ t_err | sticky | any MUST-NOT breach | official progress after human t_lock | median fidelity |",
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
L = [f"# E4 census — objective replay of every replayable annotated FAIL trajectory\n",
     f"Generated {datetime.date.today()} from `{os.path.basename(sys.argv[1])}`.\n",
     "## 1. Coverage (how we got from the corpus to the analysed set)\n",
     f"- Replayable pool: **{pool + len(orig_all)}** FAIL trajectories ({len(orig_all)} already replayed in E4 + {pool} not yet replayed) (miniswe + terminus2 with step-level action/observation logs; openhands is excluded because its exported logs drop editor payloads).",
     f"- Tasks excluded before replay: **{len(exc)} tasks / {sum(v.get('n_traj',0) for v in exc.values())} trajectories** — " + "; ".join(f"{k}: {a} tasks / {b} traj" for k, (a, b) in sorted(reason_groups.items())) + ". Per-task reasons are in `census_tasks.json`.",
     f"- Replayed: the original E4 sample ({S.get('n_sample_traj_with_runs',0)-len(cen) if False else len(orig)} valid after exclusions) plus **{len(cases)}** census cases over {len(ready)} tasks → **{S['n_sample_traj_with_runs']} trajectories with a finished replay**.",
     f"- Dropped after replay (reference solution produces no parseable test output on the pristine image, so recoverability is undefined): {len(S['excluded_baseline_oracle_fail'])} — {', '.join(sorted({c.split('__')[0] for c in S['excluded_baseline_oracle_fail']}))}.",
     f"- Relaxed baseline (reference solution passes only part of the official tests on today's image, e.g. build-cython-ext 10/11, find-official-code 1/2; recoverable(k) := the oracle reaches that same level from S_k): {sum(1 for r in rows if r.get('baseline_level'))} trajectories, flagged `baseline_level` in the rows.",
     f"- **Analysed: {len(rows)} trajectories** ({len(cen)} census + {len(orig)} original sample).\n",
     "## 2. Run hygiene\n",
     f"- Test timeouts: the first pass used a 3000 s cap per test run under heavy shared-server load. {len(rerun)} census runs hit it. Two kinds: (a) the reference solution's own training/evaluation was slow (train-fasttext, spinning-up-rl, audio-synth-stft-peaks, configure-git-webserver, fix-ocaml-gc) — these were **re-run with a 7200 s cap on an idle machine and the clean re-run replaces the first pass**; (b) the *official* test hangs on the agent's own code while the reference solution passes at the same snapshot (solve-maze-challenge, chem-rf, stable-parallel-kmeans) — a hang is scored as 'official tests not passing' and recoverability is unaffected, so these were not re-run (later snapshots were finished with a 600 s cap on the official-only run).",
     f"- Split runs (stopped and resumed from the next snapshot with the shorter official-only cap): {', '.join(k for k in splits if not k.startswith('_'))}.",
     f"- Fidelity control (unchanged from E4): {S['rule2']['pass_finals_faithful']}/{S['rule2']['pass_finals_faithful']+S['rule2']['pass_finals_unfaithful']} same-task PASS finals pass the official tests when replayed.",
     f"- Replays with at least one step timeout (command still running after 600 s): {S['runs_with_step_timeouts']}.\n",
     "## 3. Headline numbers\n", *hdr, *block("E4 sample (original)", orig), *block("census (new)", cen), *block("all analysed", rows),
     "", *hdr, *block("miniswe", [r for r in rows if r["scaffold"] == "miniswe"]), *block("terminus2", [r for r in rows if r["scaffold"] == "terminus2"]),
     "", "Sticky locks only (oracle never passes again after the first failure; the robust subset for a single replay):", *hdr,
     *block("all, sticky locks", [r for r in rows if r["t_lock_obj"] is None or all(r["sticky"])]),
     "", "terminus2 fidelity is structurally low: its 'output' is a tmux pane diff (cursor/timestamps/prompts), not a command's stdout, so similarity is not comparable across scaffolds; the strata table below shows the conclusions do not move with fidelity.",
     "", f"Original E4 report for comparison (84 valid): never locks {O['relation']['never_locks_objectively']}/84, agree ±1 {O['relation']['agree_pm1']}, human later {O['relation']['human_later']}, human earlier {O['relation']['human_earlier']}, official progress after lock {O['official_progress_after_lock']['true']}/{O['official_progress_after_lock']['true']+O['official_progress_after_lock']['false']}.\n",
     "## 3b. Where the objective lock falls relative to the human markers\n",
     "| subset | n locks | before t_err (k = t_err−1, state already unrecoverable before the annotated first error) | at t_err | inside (t_err, t_lock] | after t_lock | inside-window locks within ±1 of human t_lock |", "|---|---|---|---|---|---|---|",
     *[(lambda rs: (lambda c, w: f"| {nm} | {len(rs)} | {c['before']} | {c['at']} | {c['inside']} | {c['after']} | {sum(abs(r['t_lock_obj']-r['t_lock'])<=1 for r in w)}/{len(w)} |")(
         collections.Counter('before' if r['t_lock_obj'] < r['t_err'] else 'at' if r['t_lock_obj'] == r['t_err'] else 'inside' if r['t_lock_obj'] <= r['t_lock'] else 'after' for r in rs),
         [r for r in rs if r['t_err'] < r['t_lock_obj'] <= r['t_lock']]))(rs) for nm, rs in (("all locks", [r for r in rows if r["t_lock_obj"] is not None]), ("sticky locks", [r for r in rows if r["t_lock_obj"] is not None and all(r["sticky"])]))],
     "", "Locks *before t_err* are not disagreements about t_lock: the reference solution already fails on the snapshot taken one step before the annotated first error. They point at either an earlier unannotated state change (annotation misses) or at agent-side environment changes the reference solution does not tolerate; they need per-case inspection before being counted either way.\n",
     "## 4. Fidelity strata (does low replay fidelity change the picture?)\n",
     "| mean output similarity | n | never objectively locks | objective locks | within ±1 of human |", "|---|---|---|---|---|"]
for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, 1.01)):
    rs = [r for r in rows if r["mean_sim"] and r["mean_sim"][0] is not None and lo <= r["mean_sim"][0] < hi]
    locks = [r for r in rs if r["t_lock_obj"] is not None]
    L.append(f"| [{lo:.1f}, {min(hi,1):.1f}) | {len(rs)} | {pct(rel(rs)['never_locks_objectively'], len(rs))} | {len(locks)} | {sum(abs(r['t_lock_obj']-r['t_lock'])<=1 for r in locks)} |")
L += ["", "## 5. Objective locks — task breakdown\n", "| task | locks | n analysed | obj−human t_lock (per lock) |", "|---|---|---|---|"]
bt = collections.defaultdict(list); nt = collections.Counter(r["task"] for r in rows)
for r in rows:
    if r["t_lock_obj"] is not None: bt[r["task"]].append(r["t_lock_obj"] - r["t_lock"])
for t, v in sorted(bt.items(), key=lambda x: -len(x[1])): L.append(f"| {t} | {len(v)} | {nt[t]} | {', '.join(f'{x:+d}' for x in v)} |")
L += ["", "## 6. Reading guide\n",
      "- *never objectively locks*: the reference solution applied to every replayed snapshot in [t_err−1, t_lock+5] still passes the official tests — the task stayed solvable from the agent's state throughout; the human t_lock therefore marks a behavioural commitment, not a loss of solvability.",
      "- *objective lock*: first snapshot from which the reference solution no longer passes; *sticky* = it never passes again afterwards.",
      "- *breach*: first snapshot violating a calibrated MUST-NOT sub-test (only for the 43 tasks with sub-tests).",
      "- Fidelity = mean difflib similarity between replayed and logged step outputs; low values are mostly timestamps/pids/progress bars, see stratification above.",
      "- Caveats: single replay per census trajectory (original sample had up to 3); official-test hangs scored as not passing; relaxed-baseline rows flagged."]
open(f"{OUT_DIR}/CENSUS_REPORT.md", "w").write("\n".join(L)); print("CENSUS_REPORT.md written:", len(rows), "rows,", len(cen), "census")
