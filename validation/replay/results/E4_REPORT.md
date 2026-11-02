# E4 — Replay validation of lock-in (t_lock) — report

Generated 2026-11-02 from `analysis.json`. 84 trajectories analysed; 76 with 3 replay repetitions, 6 with 2, rest 1.

## 1. Method (what was actually run)

- **Corpus**: failed trajectories from the paper's 1,184, restricted to miniswe + terminus2 (openhands trajectories lose editor payloads), with a same-task PASS trajectory, `t_lock ≤ 40`, and no network/installation command inside the replay window → 190 candidates (45 tasks).
- **Sample**: 119 stratified (27 uncertain-annotation, 48 containing a destructive command, 29 silent/late-surfacing, 6 task-coverage, 9 long-window controls). Ten tasks excluded for environment reasons (`exclusions.json`) → 87 trajectories, 836 replay points, 34 tasks; three more dropped because the reference solution fails on the pristine image (dependency drift) → **84 analysed**.
- **Replay**: task images rebuilt from the pinned Terminal-Bench commit `d28711d0`; actions replayed step by step (miniswe: `/bin/sh -c` per step; terminus2: persistent tmux shell, text via `paste-buffer`, keystrokes recovered from the model JSON where the raw export dropped them); `docker commit` snapshot after each step k ∈ [t_err−1, t_lock+5]. Drift compensation: static `uv` injected, `PIP_BREAK_SYSTEM_PACKAGES=1`.
- **Per snapshot**: (a) official tests on S_k (progress); (b) `solution.sh` applied on S_k then official tests (**recoverable(k)**); (c) calibrated sub-tests MUST / MUST-NOT / UNTESTED. **t_lock_obj** = first k with recoverable(k)=false (majority over repetitions); **t_breach** = first k violating a MUST-NOT.
- **Sub-test calibration**: oracle passes all MUST/UNTESTED and no MUST-NOT; pristine image fails ≥1 MUST; every faithfully replayed same-task PASS trajectory passes (rule 2; dropped: git-leak-recovery 1, tmux-advanced-workflow 2, modernize-fortran-build 2, neuron-to-jaxley-conversion 4, fix-ocaml-gc 1, extract-elf 1, git-workflow-hack 1).
- **Fidelity control**: 101 PASS trajectories replayed to their final step; official tests pass in **86/99** (failures = dependency drift between the 2025 runs and today's rebuilt images).

## 2. Headline numbers (84 trajectories)

| quantity | value |
|---|---|
| reference solution still passes from **every** replayed state (no objective lock-in) | **69 / 84 (82%)** |
| objective lock-in exists | 15 / 84 (18%); sticky in 10 |
| … human t_lock within ±1 step of t_lock_obj | 5 |
| … human t_lock later than objective | 7 |
| … human t_lock earlier than objective | 3 |
| MUST-NOT breach | 22 / 84; at/before t_err: 14, inside fix window: 4, after human lock: 4 |
| official-test pass count rises after human t_lock | 12 / 79 (15%) |
| MUST pass count rises after human t_lock | 16 / 79 (20%) |
| across-repetition agreement on t_lock_obj | 91% |
| by scaffold, no objective lock | miniswe 41/50, terminus2 28/34 |
| uncertain-annotation tier | {"never_locks_objectively": 10, "human_later": 3} |
| destructive-command tier | {"never_locks_objectively": 34, "human_earlier": 3, "agree_pm1": 4, "human_later": 2} |

## 3. The 15 objectively-locking trajectories

| trajectory | tier | t_err | t_lock (human) | t_lock_obj | sticky | MUST-NOT breach | what broke the reference solution |
|---|---|---|---|---|---|---|---|
| fix-ocaml-gc__miniswe__claude | uncertain | 13 | 27 | 15 | False | — | agent edits to the runtime/build system that solution.sh does not revert |
| fix-ocaml-gc__miniswe__gemini | destructive | 18 | 25 | 25 | True | 27 | agent edits to the runtime/build system that solution.sh does not revert |
| fix-ocaml-gc__miniswe__kimi | destructive | 35 | 38 | 38 | False | — | agent edits to the runtime/build system that solution.sh does not revert |
| fix-ocaml-gc__terminus2__kimi | destructive | 20 | 36 | 41 | False | — | agent edits to the runtime/build system that solution.sh does not revert |
| git-leak-recovery__terminus2__gpt5 | destructive | 9 | 11 | 11 | True | — | git history rewritten so the reference recovery no longer finds the flag |
| git-workflow-hack__miniswe__devstral | destructive | 18 | 29 | 18 | True | 18 | workflow file deleted (reference `sed`s it) |
| intrusion-detection__miniswe__gemini | destructive | 14 | 14 | 19 | False | 19 | logs/rules modified after lock-in |
| mahjong-winninghand__miniswe__gemini | destructive | 8 | 9 | 8 | True | 9 | extra result files written; reference does not clean them |
| neuron-to-jaxley-conversion__miniswe__gemini | destructive | 4 | 4 | 7 | True | 4 | RGC template rewritten (reference appends to it with `cat >>`) |
| neuron-to-jaxley-conversion__terminus2__claude | uncertain | 5 | 22 | 5 | False | 5 | RGC template rewritten (reference appends to it with `cat >>`) |
| neuron-to-jaxley-conversion__terminus2__qwen | control_long_window | 10 | 16 | 10 | True | 10 | RGC template rewritten (reference appends to it with `cat >>`) |
| reshard-c4-data__miniswe__deepseek-v3.2 | uncertain | 6 | 8 | 5 | True | — | agent-created pyproject/uv state breaks the reference `uv` flow (oracle brittleness) |
| reshard-c4-data__miniswe__devstral | destructive | 10 | 11 | 9 | True | — | agent-created pyproject/uv state breaks the reference `uv` flow (oracle brittleness) |
| reshard-c4-data__terminus2__devstral | control_long_window | 6 | 19 | 5 | True | — | agent-created pyproject/uv state breaks the reference `uv` flow (oracle brittleness) |
| reshard-c4-data__terminus2__gemini | silent_or_late | 13 | 13 | 12 | True | — | agent-created pyproject/uv state breaks the reference `uv` flow (oracle brittleness) |

Breach alignment: 5 lock-ins coincide (±1) with a MUST-NOT breach, 1 have an earlier breach, 9 none (reshard-c4-data cases are reference brittleness to pre-existing project files rather than true unrecoverability).

## 4. Interpretation for the paper

1. **Reviewer B is right that `t_lock` is not environmental unrecoverability.** In 82% of replayed failures the reference solution still passes from every state in the window: the environment never became unrecoverable; the *agent* stopped revisiting. Keep the descriptive definition ("no subsequent recovery observed"); delete every "no remaining path to success" / "irreversible" phrasing.
2. **The descriptive point is not vacuous.** After the annotated lock-in step the official pass count rises in only 15% of trajectories and the MUST count in 20%. Objective lock-ins, when they occur, come from the agent destroying or rewriting provided artifacts: 6/15 coincide with or follow a MUST-NOT breach; the rest are edits to provided files not covered by a MUST-NOT test, or reference-solution brittleness.
3. **A second, objective marker is available: the first MUST-NOT breach**, present in 22/84 trajectories and at or before the annotated decisive error in 14 of them — state-side support for t_err.
4. **Human lock-in tends to be later, not earlier, than the objective one** (7 later vs 3 earlier), so the annotated fix window is conservative.
5. **By-products**: 16 cases (12 tasks) where the reference solution or official tests violate or ignore stated requirements (`CALIBRATION_SUMMARY.md`); replay fidelity 87%; dependency drift is the dominant threat to replaying 2025 trajectories in 2026.

## 5. Limitations to state

- Replay window limited to [t_err−1, t_lock+5]; objective lock-in after the window is not observed.
- "Recoverable" = *reference solution passes from the state*; a brittle reference under-estimates recoverability, a robust one over-estimates it.
- `docker commit` snapshots lose POSIX ACLs and process state (services, tmux sessions); such tasks were excluded.
- Drift compensation and ~13% unfaithful PASS replays; openhands excluded → two of three scaffolds.
- Heavy tasks (fix-ocaml-gc, triton-interpret) have fewer repetitions.

Excluded tasks (10): `create-bucket` — localstack ENTRYPOINT + in-memory bucket state not captured by docker commit; `mteb-eval` — image broken by dependency drift (transformers 5.x), oracle cannot run; `parallelize-graph` — oracle rebuilds Berkeley UPC (~10 min) per snapshot; cost prohibitive; `word2vec-from-scratch` — Dockerfile downloads HF dataset at build time; build fails on both hosts; `build-linux-kernel-qemu` — kernel build per snapshot is hours; oracle produces no bzImage under emulation; `mcmc-sampling-stan` — oracle cannot install rstan (cmake missing in image); 4x100k MCMC exceeds test timeout; `vul-flink` — oracle is a ~45 min networked maven build; per-snapshot cost prohibitive; `mteb-retrieve` — image broken by dependency drift (transformers 5.x); oracle exits 1 on pristine image; `acl-permissions-inheritance` — POSIX ACL xattrs do not survive docker commit snapshots (verified: 13 ACL entries -> 6 after commit); state cannot be snapshotted faithfully; `query-optimize` — official test executes a ~190 s query twice per snapshot; 4 trajectories x ~17 snapshots x 3 reps is >20 h; cost prohibitive