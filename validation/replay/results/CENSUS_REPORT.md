# E4 census — objective replay of every replayable annotated FAIL trajectory

Generated 2026-11-02 from `census_analysis.json`.

## 1. Coverage (how we got from the corpus to the analysed set)

- Replayable pool: **626** FAIL trajectories (87 already replayed in E4 + 539 not yet replayed) (miniswe + terminus2 with step-level action/observation logs; openhands is excluded because its exported logs drop editor payloads).
- Tasks excluded before replay: **23 tasks / 186 trajectories** — image cannot be rebuilt / oracle cannot run today (dependency drift, dead downloads): 6 tasks / 45 traj; prohibitive per-snapshot cost: 5 tasks / 40 traj; reference solution fails the official tests on today's rebuilt image: 10 tasks / 88 traj; state cannot be snapshotted faithfully (docker commit loses it): 2 tasks / 13 traj. Per-task reasons are in `census_tasks.json`.
- Replayed: the original E4 sample (85 valid after exclusions) plus **353** census cases over 53 tasks → **440 trajectories with a finished replay**.
- Dropped after replay (reference solution produces no parseable test output on the pristine image, so recoverability is undefined): 6 — incompatible-python-fasttext.
- Relaxed baseline (reference solution passes only part of the official tests on today's image, e.g. build-cython-ext 10/11, find-official-code 1/2; recoverable(k) := the oracle reaches that same level from S_k): 21 trajectories, flagged `baseline_level` in the rows.
- **Analysed: 434 trajectories** (349 census + 85 original sample).

## 2. Run hygiene

- Test timeouts: the first pass used a 3000 s cap per test run under heavy shared-server load. 24 census runs hit it. Two kinds: (a) the reference solution's own training/evaluation was slow (train-fasttext, spinning-up-rl, audio-synth-stft-peaks, configure-git-webserver, fix-ocaml-gc) — these were **re-run with a 7200 s cap on an idle machine and the clean re-run replaces the first pass**; (b) the *official* test hangs on the agent's own code while the reference solution passes at the same snapshot (solve-maze-challenge, chem-rf, stable-parallel-kmeans) — a hang is scored as 'official tests not passing' and recoverability is unaffected, so these were not re-run (later snapshots were finished with a 600 s cap on the official-only run).
- Split runs (stopped and resumed from the next snapshot with the shorter official-only cap): stable-parallel-kmeans__miniswe__deepseek-v3.2, stable-parallel-kmeans__miniswe__kimi, chem-rf__terminus2__kimi, fix-ocaml-gc__miniswe__devstral.
- Fidelity control (unchanged from E4): 86/99 same-task PASS finals pass the official tests when replayed.
- Replays with at least one step timeout (command still running after 600 s): 19.

## 3. Headline numbers

| group | n valid | never objectively locks | objective locks | obj within ±1 of human t_lock | within ±3 | obj earlier than human (>1) | obj later than human (>1) | obj lock ≥ t_err | sticky | any MUST-NOT breach | official progress after human t_lock | median fidelity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E4 sample (original) | 85 | 69 (81.2%) | 16 | 5 | 8 | 10 | 3 | 11 | 10 | 21 | 12/80 | 0.57 |
| census (new) | 349 | 298 (85.4%) | 51 | 21 | 26 | 33 | 4 | 33 | 36 | 16 | 33/342 | 0.35 |
| all analysed | 434 | 367 (84.6%) | 67 | 26 | 34 | 43 | 7 | 44 | 46 | 37 | 45/422 | 0.38 |

| group | n valid | never objectively locks | objective locks | obj within ±1 of human t_lock | within ±3 | obj earlier than human (>1) | obj later than human (>1) | obj lock ≥ t_err | sticky | any MUST-NOT breach | official progress after human t_lock | median fidelity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| miniswe | 229 | 195 (85.2%) | 34 | 16 | 23 | 21 | 4 | 22 | 25 | 24 | 32/220 | 0.66 |
| terminus2 | 205 | 172 (83.9%) | 33 | 10 | 11 | 22 | 3 | 22 | 21 | 13 | 13/202 | 0.17 |

Sticky locks only (oracle never passes again after the first failure; the robust subset for a single replay):
| group | n valid | never objectively locks | objective locks | obj within ±1 of human t_lock | within ±3 | obj earlier than human (>1) | obj later than human (>1) | obj lock ≥ t_err | sticky | any MUST-NOT breach | official progress after human t_lock | median fidelity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all, sticky locks | 413 | 367 (88.9%) | 46 | 23 | 29 | 28 | 4 | 28 | 46 | 35 | 43/401 | 0.39 |

terminus2 fidelity is structurally low: its 'output' is a tmux pane diff (cursor/timestamps/prompts), not a command's stdout, so similarity is not comparable across scaffolds; the strata table below shows the conclusions do not move with fidelity.

Original E4 report for comparison (84 valid): never locks 69/84, agree ±1 5, human later 7, human earlier 3, official progress after lock 12/79.

## 3b. Where the objective lock falls relative to the human markers

| subset | n locks | before t_err (k = t_err−1, state already unrecoverable before the annotated first error) | at t_err | inside (t_err, t_lock] | after t_lock | inside-window locks within ±1 of human t_lock |
|---|---|---|---|---|---|---|
| all locks | 67 | 23 | 9 | 23 | 12 | 10/23 |
| sticky locks | 46 | 18 | 8 | 13 | 7 | 9/13 |

Locks *before t_err* are not disagreements about t_lock: the reference solution already fails on the snapshot taken one step before the annotated first error. They point at either an earlier unannotated state change (annotation misses) or at agent-side environment changes the reference solution does not tolerate; they need per-case inspection before being counted either way.

## 4. Fidelity strata (does low replay fidelity change the picture?)

| mean output similarity | n | never objectively locks | objective locks | within ±1 of human |
|---|---|---|---|---|
| [0.0, 0.2) | 126 | 106 (84.1%) | 20 | 4 |
| [0.2, 0.4) | 100 | 80 (80.0%) | 20 | 10 |
| [0.4, 0.6) | 73 | 65 (89.0%) | 8 | 2 |
| [0.6, 1.0) | 135 | 116 (85.9%) | 19 | 10 |

## 5. Objective locks — task breakdown

| task | locks | n analysed | obj−human t_lock (per lock) |
|---|---|---|---|
| spinning-up-rl | 9 | 11 | +2, -4, -18, -27, -25, -1, -9, -1, +0 |
| fix-ocaml-gc | 7 | 11 | -5, +0, +0, +5, -12, -3, -11 |
| find-official-code | 6 | 14 | +0, -6, +1, +1, +0, -2 |
| db-wal-recovery | 5 | 7 | -4, -4, -1, -3, -25 |
| neuron-to-jaxley-conversion | 4 | 10 | +3, -17, -6, +0 |
| reshard-c4-data | 4 | 4 | -14, -3, -1, -2 |
| build-cython-ext | 3 | 12 | -8, +0, -1 |
| audio-synth-stft-peaks | 3 | 13 | -18, -5, +4 |
| git-multibranch | 3 | 6 | -12, -198, +0 |
| extract-moves-from-video | 3 | 7 | -16, +0, +1 |
| gpt2-codegolf | 2 | 14 | +2, -1 |
| count-dataset-tokens | 2 | 12 | -4, -4 |
| flood-monitoring-basic | 2 | 5 | +0, +0 |
| chess-best-move | 2 | 13 | -27, -17 |
| intrusion-detection | 1 | 9 | +5 |
| git-leak-recovery | 1 | 1 | +0 |
| triton-interpret | 1 | 12 | +1 |
| git-workflow-hack | 1 | 4 | -11 |
| train-fasttext | 1 | 12 | -26 |
| mahjong-winninghand | 1 | 3 | -1 |
| hf-lora-adapter | 1 | 6 | -1 |
| cross-entropy-method | 1 | 1 | -1 |
| configure-git-webserver | 1 | 4 | -12 |
| multi-source-data-merger | 1 | 2 | +1 |
| chem-rf | 1 | 9 | +4 |
| rare-mineral-allocation | 1 | 6 | -6 |

## 6. Reading guide

- *never objectively locks*: the reference solution applied to every replayed snapshot in [t_err−1, t_lock+5] still passes the official tests — the task stayed solvable from the agent's state throughout; the human t_lock therefore marks a behavioural commitment, not a loss of solvability.
- *objective lock*: first snapshot from which the reference solution no longer passes; *sticky* = it never passes again afterwards.
- *breach*: first snapshot violating a calibrated MUST-NOT sub-test (only for the 43 tasks with sub-tests).
- Fidelity = mean difflib similarity between replayed and logged step outputs; low values are mostly timestamps/pids/progress bars, see stratification above.
- Caveats: single replay per census trajectory (original sample had up to 3); official-test hangs scored as not passing; relaxed-baseline rows flagged.