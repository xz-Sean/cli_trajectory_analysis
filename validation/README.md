# Validation of the annotations

This directory holds everything behind Section II-E/II-F of the revised paper: the objective
checks we ran on the human annotations after the first submission, the inputs they used, the raw
outputs they produced, and the scripts that turn those outputs into the numbers in the paper.

Nothing here depends on an annotator. The checks compare the annotated time points with
(a) the state of the task environment, rebuilt and replayed step by step (`replay/`),
(b) rule-based detectors run over the trajectory text (`static_checks/`),
(c) the earlier v1 annotation round (`codebook_history/`), and
(d) the Terminal-Bench task list, to audit which tasks the corpus kept (`corpus_filtering/`).

```
validation/
  replay/              E4: environment replay of 434 failed trajectories (the main check)
    scripts/           replayer, calibration, census driver, merge, analysis, report scripts
    subtests/<task>/   calibrated MUST / MUST-NOT / UNTESTED sub-tests + per-task CALIBRATION.md
    calib/             pristine-image and reference-solution calibration record per task
    inputs/            which trajectories were replayed, with t_err / t_lock, and why tasks were excluded
    runs/              727 raw replay result files (one per trajectory and repetition)
    results/           aggregated analysis (json) and the reports rendered from it (md)
  static_checks/       E1: rule-based t_surface detector, evidence-quote localisation, fabrication, action codes
  codebook_history/    E6: v1 schema, v1 -> v2 field mapping, codebook history
  corpus_filtering/    E7: Terminal-Bench task metadata and the audit of the task filter
```

## 1. Replay (`replay/`)

### What it does

For every annotated FAIL trajectory whose environment can be rebuilt and whose commands can be
re-executed, we rebuild the task container from the Terminal-Bench task definition (commit
`d28711d0`), re-run the agent's commands in order, and take a container snapshot after every step
in the window `[t_err - 1, t_lock + 5]` (capped at the last step). On every snapshot we run

1. the official tests (pass count = task progress),
2. the official reference solution `solution.sh` followed by the official tests
   (`recoverable(k)` = the task is still solvable from this state), and
3. for 32 tasks, calibrated sub-tests that check required (MUST), forbidden (MUST-NOT) and
   instruction-stated-but-officially-untested (UNTESTED) properties of the environment.

Derived per trajectory: `t_lock_obj` = first snapshot where the reference solution fails,
`sticky` = it never passes again inside the window, `breach` = first snapshot where a MUST-NOT
sub-test fails that passed on the pristine snapshot.

### Coverage

| step | n |
|---|---|
| failed trajectories in the paper | 1,184 |
| OpenHands logs do not record command contents, cannot be replayed | -558 |
| MiniSWE + Terminus2 failed trajectories (replay pool) | 626 |
| excluded at task level (23 tasks; reasons in `inputs/census_tasks.json`) | -186 |
| replayed | 440 |
| reference solution produces no parsable test output on the pristine image (`incompatible-python-fasttext`) | -6 |
| **analysed** | **434** (53 tasks, 7 models, 2 scaffolds; 210 of them in the 32 tasks with sub-tests) |

The 23 excluded tasks fall into four groups: image cannot be rebuilt or the reference solution no
longer runs today (6 tasks / 45 trajectories); the reference solution does not pass the official
tests on a clean rebuilt image (10 / 88); one snapshot costs tens of minutes or more (5 / 40); the
relevant state does not survive `docker commit`, e.g. POSIX ACLs, in-memory services (2 / 13).

### Rules that affect the numbers

- **Baseline.** A trajectory enters the analysis only if the reference solution passes the official
  tests on the pristine rebuilt image (`baseline_oracle_ok`). For two tasks whose reference solution
  deterministically passes only part of the tests (`build-cython-ext` 10/11, `find-official-code`
  1/2), `E4_RELAX_BASELINE=1` defines recoverable as "reaches the pristine level" (`baseline_level`
  in the rows).
- **Sub-test calibration** (`CALIBRATION_NOTES.md`, per-task `subtests/<task>/CALIBRATION.md`):
  rule 1, the reference solution passes every MUST/UNTESTED and violates no MUST-NOT; rule 3, at
  least one MUST fails on the pristine image. Sub-tests violating these were rewritten or dropped;
  every drop is logged. Sub-tests were drafted by LLM coding agents following
  `SUBTEST_AUTHORING_BRIEF.md`, then calibrated and reviewed.
- **Rule 2 (replay).** Sub-tests that fail on faithfully replayed same-task PASS finals are dropped
  for that task (`summary.rule2.dropped_subtests`).
- **Rule 3' (replay, per trajectory).** A MUST-NOT test already failing on the pristine snapshot
  of that replay is ignored for that trajectory (`k0_mustnot_excluded`); it reflects image
  nondeterminism, not an agent action.
- **Timeouts.** Tests run with a 3000 s limit on the shared machine; 12 trajectories whose
  reference solution is slow were re-run cleanly with 7200 s and the clean run replaces the first
  (`inputs/census_rerun_timeouts.json`). Where the official tests hang on the agent's own code
  (`solve-maze-challenge`, `chem-rf`, `stable-parallel-kmeans`) the snapshot is scored as "official
  tests not passing"; the reference-solution run is unaffected (`E4_OFFICIAL_TIMEOUT`).
- **Split runs.** Four long trajectories were replayed in two parts and merged
  (`inputs/census_splits.json`, `merged_from` in the run file).
- **Fidelity.** 99 PASS trajectories of the same tasks were replayed to their last step; 86 pass the
  official tests again, the 13 that do not fail because of dependency drift in the rebuilt images.
  Each replayed step also records `out_sim`, the text similarity of the replayed output to the
  logged one; Terminus2 similarity is structurally low (tmux pane diffs), so compare it only within
  a scaffold.

### Headline numbers (`results/VALIDATION.md`, `results/CENSUS_REPORT.md`)

| | |
|---|---|
| reference solution passes at every snapshot, t_err-1 .. t_lock+5 | 367 / 434 (84.6%) |
| t_err contradicted: uncorrected objective error already present before t_err | 21 / 434 (4.8%) |
| t_lock contradicted: environment repaired after t_lock | 5 / 434 (1.2%) |
| official pass count rises after t_lock | 45 / 422 (equal 5-step windows, n = 99: 10 before vs 4 after) |
| first forbidden action (37 trajectories): before / at t_err / inside window / after t_lock | 5 / 18 / 8 / 6 |
| reference solution fails at some step (67; 46 never pass again): before / at t_err / inside / after | 23 / 9 / 23 / 12 |

`results/census_locks_before_t_err.json` lists the 23 trajectories whose state is already
unrecoverable one step before the annotated t_err (18 sticky; 13 of them in `spinning-up-rl`,
`reshard-c4-data`, `db-wal-recovery`).

### Reproduce the numbers from the shipped run files (no Docker needed, ~1 min)

Run from the package root. The three commands regenerate `results/census_analysis.json`,
`results/CENSUS_REPORT.md`, `results/VALIDATION.md` and `results/validation.json`; we verified the
regenerated files are identical to the shipped ones (up to list order and the date line).

```bash
cd validation/replay
E4_RELAX_BASELINE=1 python3 scripts/e4_analyze.py runs inputs/census_sample.json inputs/pass_finals_all.json results/census_analysis.json
python3 scripts/e4_census_report.py results/census_analysis.json results/analysis.json inputs
python3 scripts/e4_validation_table.py results/census_analysis.json runs results/VALIDATION.md results/validation.json subtests
# pilot report (the 87-trajectory sample replayed first; its analysis.json is the second input above)
python3 scripts/e4_report.py results/analysis.json inputs/exclusions.json
```

### Re-run the replay itself (Docker, hours per task)

`e4_replay.py` works inside a work directory `$E4_ROOT` laid out as

```
$E4_ROOT/
  merged_trajectories/<task>/<scaffold>/<model>/step_<k>.jsonl   raw trajectories (released separately)
  trajrepair_extraction/corpus_RPO.json                           per-step commands extracted from the raw logs
  resub/tb_tasks/terminal-bench/original-tasks/<task>/            Terminal-Bench tasks at commit d28711d0
  resub/e4/subtests/                                              copy of validation/replay/subtests
  resub/e4/calib/                                                 written by calibration
  resub/e4/runs/                                                  written by replay
  resub/tools/uv-{x86_64,aarch64}                                 uv binaries used to pre-build test venvs
```

```bash
export E4_ROOT=/path/to/workdir
python3 e4_replay.py build <task>                      # rebuild the task image
python3 e4_calibrate.py <task>                         # pristine / reference-solution calibration of the sub-tests
python3 e4_prebake.py <task>                           # optional: pre-build the test venv once
python3 e4_census.py prepare <task>; python3 e4_census.py status; python3 e4_census.py cases
python3 e4_replay.py replay <cid> --kmin K --kmax K --rep N
python3 e4_census_merge.py <all_runs> <census_runs> <out_dir>
```

Environment knobs: `E4_TEST_TIMEOUT` (default 900 s), `E4_OFFICIAL_TIMEOUT`, `E4_CACHE_DIR`,
`E4_VENV_DIR`. The shell dispatchers we used on a shared machine are operational glue and are not
shipped. `e4_recover.py` recovers the Terminus2 command text that the original export dropped for
4,247 Devstral/Gemini steps.

### Run file format (`runs/<cid>__rep<N>.json`)

`cid` = `<task>__<scaffold>__<model>`; `steps[]` = `{k, type, secs, out_sim, out_tail}` for every
re-executed step; `eval["<k>"]` for `k = 0` (pristine) and every snapshot in the window:
`tests` = official tests `{passed, failed, total, passed_names, failed_names, raw_tail}` plus
`tests.sub.{must,mustnot,untested}`; `oracle` = the same after applying the reference solution.

## 2. Static checks (`static_checks/`, E1)

Rule-based detectors run over the trajectory text, compared with the human labels:
`e1_1_tsurface.py` (first observable failure signal; auto 23.6% silent vs human 28.0%),
`e1_2_evidence.py` (are `*_evidence` quotes verbatim? exact 3.8%, fragment 35.7%; the codebook
now describes them as grounded descriptions with quoted fragments), `e1_3_fabrication.py`,
`e1_4_segments.py` (command-level action codes vs human `action_segments`). Results:
`VALIDATION_STATIC.md` and the json/csv files. Re-running needs the raw trajectories:
`TRAJ_DIR=/path/to/merged_trajectories python3 scripts/e1_1_tsurface.py` (same for the others).

## 3. Codebook history (`codebook_history/`, E6)

The v1 annotation round (355 + 826 records, shipped in `data/v1_annotations/`) and its mapping to
the v2 schema: `v1_schema.md`, `v1_to_v2_mapping.md`, `CODEBOOK_HISTORY.md`. Key finding: the v1
single marker `n` matches v2 `t_err` (57%) more often than `t_commit` (46%), so the v2 time points
were re-annotated rather than inherited. Regenerate with
`cd codebook_history/scripts && python3 e6_schema.py && python3 e6_mapping.py && python3 e6_history.py`.

## 4. Corpus filtering audit (`corpus_filtering/`, E7)

`tb_task_metadata.csv` (241 Terminal-Bench tasks at `d28711d0`), `metadata_reconciliation.md`
(task metadata vs the paper's 89 tasks) and `filtering_audit.md` (the complete-grid filter retains
harder tasks: hard 33.7% of kept vs 17.8% of dropped tasks, p = 0.017; category mix p = 0.43;
1,869 -> 1,860 -> 1,794 accounting). Scripts take explicit paths:

```bash
python3 scripts/e7_task_metadata.py <terminal-bench/tasks dir> tb_task_metadata.csv
python3 scripts/e7_reconcile.py tb_task_metadata.csv ../../data/merged_tasks.json terminal_bench_task_stats.md ../../data/traj_data_v2_all89tasks.json metadata_reconciliation.md metadata_reconciliation.json
python3 scripts/e7_filtering_audit.py tb_task_metadata.csv ../../data/merged_tasks.json <merged_trajectories dir> ../../data/traj_data_v2_all89tasks.json filtering_audit.md filtering_audit.json
```

## What these checks do not establish

They measure the relation between the annotated time points and the environment state, not
agreement between annotators; they cover `t_err` and `t_lock` only, not `t_surface` or the
categorical labels; the replay covers MiniSWE and Terminus2 failed trajectories only; "recoverable"
uses the official reference solution as the single repair path; census trajectories were replayed
once (the 87-trajectory pilot three times, 91% agreement across repetitions).
