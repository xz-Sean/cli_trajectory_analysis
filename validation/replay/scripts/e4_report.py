#!/usr/bin/env python3
"""Render resub/e4/E4_REPORT.md from analysis.json (run after e4_analyze.py)."""
import json, collections, datetime, os
import sys
AN, EXC = sys.argv[1], sys.argv[2]  # analysis.json, exclusions.json
R = os.path.dirname(os.path.abspath(AN))
A = json.load(open(AN)); S = A["summary"]; rows = [r for r in A["rows"] if r["baseline_oracle_ok"] is not False]
ex = json.load(open(EXC)); n = len(rows)
locks = [r for r in rows if r["t_lock_obj"] is not None]
def rel_breach(r):
    b, o = r["breach"], r["t_lock_obj"]
    return "breach_coincides" if b is not None and abs(b - o) <= 1 else ("breach_before" if b is not None and b < o else "no_breach_at_lock")
cnt = collections.Counter(rel_breach(r) for r in locks)
what = {"fix-ocaml-gc": "agent edits to the runtime/build system that solution.sh does not revert", "git-leak-recovery": "git history rewritten so the reference recovery no longer finds the flag", "git-workflow-hack": "workflow file deleted (reference `sed`s it)", "intrusion-detection": "logs/rules modified after lock-in", "mahjong-winninghand": "extra result files written; reference does not clean them", "neuron-to-jaxley-conversion": "RGC template rewritten (reference appends to it with `cat >>`)", "reshard-c4-data": "agent-created pyproject/uv state breaks the reference `uv` flow (oracle brittleness)"}
po = S["official_progress_after_lock"]; pm = S["must_progress_after_lock"]
pot = po.get("true", 0) + po.get("false", 0); pmt = pm.get("true", 0) + pm.get("false", 0)
nb = sum(1 for r in rows if r["breach"] is not None)
fid = S["rule2"]["pass_finals_faithful"]; fidt = fid + S["rule2"]["pass_finals_unfaithful"]
L = [f"# E4 — Replay validation of lock-in (t_lock) — report\n",
     f"Generated {datetime.date.today()} from `analysis.json`. {n} trajectories analysed; {S['n_with_3_reps']} with 3 replay repetitions, {S['n_with_2_reps']} with 2, rest 1.\n",
     "## 1. Method (what was actually run)\n",
     "- **Corpus**: failed trajectories from the paper's 1,184, restricted to miniswe + terminus2 (openhands trajectories lose editor payloads), with a same-task PASS trajectory, `t_lock ≤ 40`, and no network/installation command inside the replay window → 190 candidates (45 tasks).",
     f"- **Sample**: 119 stratified (27 uncertain-annotation, 48 containing a destructive command, 29 silent/late-surfacing, 6 task-coverage, 9 long-window controls). Ten tasks excluded for environment reasons (`exclusions.json`) → 87 trajectories, 836 replay points, 34 tasks; three more dropped because the reference solution fails on the pristine image (dependency drift) → **{n} analysed**.",
     "- **Replay**: task images rebuilt from the pinned Terminal-Bench commit `d28711d0`; actions replayed step by step (miniswe: `/bin/sh -c` per step; terminus2: persistent tmux shell, text via `paste-buffer`, keystrokes recovered from the model JSON where the raw export dropped them); `docker commit` snapshot after each step k ∈ [t_err−1, t_lock+5]. Drift compensation: static `uv` injected, `PIP_BREAK_SYSTEM_PACKAGES=1`.",
     "- **Per snapshot**: (a) official tests on S_k (progress); (b) `solution.sh` applied on S_k then official tests (**recoverable(k)**); (c) calibrated sub-tests MUST / MUST-NOT / UNTESTED. **t_lock_obj** = first k with recoverable(k)=false (majority over repetitions); **t_breach** = first k violating a MUST-NOT.",
     "- **Sub-test calibration**: oracle passes all MUST/UNTESTED and no MUST-NOT; pristine image fails ≥1 MUST; every faithfully replayed same-task PASS trajectory passes (rule 2; dropped: " + ", ".join(f"{t} {len(v)}" for t, v in S["rule2"]["dropped_subtests"].items() if v) + ").",
     f"- **Fidelity control**: 101 PASS trajectories replayed to their final step; official tests pass in **{fid}/{fidt}** (failures = dependency drift between the 2025 runs and today's rebuilt images).\n",
     f"## 2. Headline numbers ({n} trajectories)\n", "| quantity | value |", "|---|---|",
     f"| reference solution still passes from **every** replayed state (no objective lock-in) | **{S['relation']['never_locks_objectively']} / {n} ({100*S['relation']['never_locks_objectively']/n:.0f}%)** |",
     f"| objective lock-in exists | {len(locks)} / {n} ({100*len(locks)/n:.0f}%); sticky in {S['sticky_when_locks']} |",
     f"| … human t_lock within ±1 step of t_lock_obj | {S['relation'].get('agree_pm1',0)} |",
     f"| … human t_lock later than objective | {S['relation'].get('human_later',0)} |",
     f"| … human t_lock earlier than objective | {S['relation'].get('human_earlier',0)} |",
     f"| MUST-NOT breach | {nb} / {n}; at/before t_err: {S['breach_rel'].get('le_t_err',0)}, inside fix window: {S['breach_rel'].get('in_window',0)}, after human lock: {S['breach_rel'].get('after_lock',0)} |",
     f"| official-test pass count rises after human t_lock | {po.get('true',0)} / {pot} ({100*po.get('true',0)/pot:.0f}%) |",
     f"| MUST pass count rises after human t_lock | {pm.get('true',0)} / {pmt} ({100*pm.get('true',0)/pmt:.0f}%) |",
     f"| across-repetition agreement on t_lock_obj | {100*S['rep_consistent_share']:.0f}% |",
     f"| by scaffold, no objective lock | miniswe {S['relation_by_scaffold']['miniswe'].get('never_locks_objectively',0)}/{sum(S['relation_by_scaffold']['miniswe'].values())}, terminus2 {S['relation_by_scaffold']['terminus2'].get('never_locks_objectively',0)}/{sum(S['relation_by_scaffold']['terminus2'].values())} |",
     f"| uncertain-annotation tier | {json.dumps(S['relation_by_tier'].get('uncertain'))} |",
     f"| destructive-command tier | {json.dumps(S['relation_by_tier'].get('destructive'))} |\n",
     f"## 3. The {len(locks)} objectively-locking trajectories\n",
     "| trajectory | tier | t_err | t_lock (human) | t_lock_obj | sticky | MUST-NOT breach | what broke the reference solution |", "|---|---|---|---|---|---|---|---|"]
for r in sorted(locks, key=lambda r: r["cid"]):
    L.append(f"| {r['cid']} | {r['why']} | {r['t_err']} | {r['t_lock']} | {r['t_lock_obj']} | {all(r['sticky'])} | {r['breach'] if r['breach'] is not None else '—'} | {what.get(r['task'],'')} |")
L += [f"\nBreach alignment: {cnt['breach_coincides']} lock-ins coincide (±1) with a MUST-NOT breach, {cnt['breach_before']} have an earlier breach, {cnt['no_breach_at_lock']} none (reshard-c4-data cases are reference brittleness to pre-existing project files rather than true unrecoverability).\n",
      "## 4. Interpretation for the paper\n",
      f"1. **Reviewer B is right that `t_lock` is not environmental unrecoverability.** In {100*S['relation']['never_locks_objectively']/n:.0f}% of replayed failures the reference solution still passes from every state in the window: the environment never became unrecoverable; the *agent* stopped revisiting. Keep the descriptive definition (\"no subsequent recovery observed\"); delete every \"no remaining path to success\" / \"irreversible\" phrasing.",
      f"2. **The descriptive point is not vacuous.** After the annotated lock-in step the official pass count rises in only {100*po.get('true',0)/pot:.0f}% of trajectories and the MUST count in {100*pm.get('true',0)/pmt:.0f}%. Objective lock-ins, when they occur, come from the agent destroying or rewriting provided artifacts: {cnt['breach_coincides']+cnt['breach_before']}/{len(locks)} coincide with or follow a MUST-NOT breach; the rest are edits to provided files not covered by a MUST-NOT test, or reference-solution brittleness.",
      f"3. **A second, objective marker is available: the first MUST-NOT breach**, present in {nb}/{n} trajectories and at or before the annotated decisive error in {S['breach_rel'].get('le_t_err',0)} of them — state-side support for t_err.",
      f"4. **Human lock-in tends to be later, not earlier, than the objective one** ({S['relation'].get('human_later',0)} later vs {S['relation'].get('human_earlier',0)} earlier), so the annotated fix window is conservative.",
      f"5. **By-products**: 16 cases (12 tasks) where the reference solution or official tests violate or ignore stated requirements (`CALIBRATION_SUMMARY.md`); replay fidelity {100*fid/fidt:.0f}%; dependency drift is the dominant threat to replaying 2025 trajectories in 2026.\n",
      "## 5. Limitations to state\n",
      "- Replay window limited to [t_err−1, t_lock+5]; objective lock-in after the window is not observed.",
      "- \"Recoverable\" = *reference solution passes from the state*; a brittle reference under-estimates recoverability, a robust one over-estimates it.",
      "- `docker commit` snapshots lose POSIX ACLs and process state (services, tmux sessions); such tasks were excluded.",
      "- Drift compensation and ~13% unfaithful PASS replays; openhands excluded → two of three scaffolds.",
      "- Heavy tasks (fix-ocaml-gc, triton-interpret) have fewer repetitions.\n",
      f"Excluded tasks ({len(ex['excluded_tasks'])}): " + "; ".join(f"`{t}` — {ex['reasons'][t]}" for t in ex["excluded_tasks"])]
open(f"{R}/E4_REPORT.md", "w").write("\n".join(L)); print("E4_REPORT.md written:", n, "trajectories,", len(locks), "locks")
