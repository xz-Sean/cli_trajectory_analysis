# Replication Package — *Failure as a Process: An Anatomy of CLI Coding Agent Trajectories*

This package reproduces every figure, table, and finding in the paper from the released
**annotated dataset** (1,794 trajectories). Every result below is computed from the annotations.

## Contents
```
data/       annotated dataset (1,794 runs) + task metadata     (NO raw trajectories)
scripts/    analysis + figure scripts (one per paper artifact) + palette.py
results/    precomputed intermediate outputs (.json / .csv)
figures/    paper figures (.pdf / .png)
docs/       codebook / schema, terminology, oracle variants
logos/      model & scaffold logos used by Fig. 2
validation/ objective checks of the annotations (environment replay, static checks,
            codebook history, corpus-filter audit) -- see validation/README.md
```

**Revised version.** This release adds `validation/` and `data/v1_annotations/`. The earlier
inter-annotator agreement files were removed: each trajectory was reviewed by one annotator, so no
per-annotator duplicate annotations exist; annotation quality is instead checked against
annotator-independent evidence (Section II-E/II-F of the paper, `validation/README.md`).

## Requirements
Python 3.10+, `numpy`, `matplotlib`, `scipy`. Run **all commands from the package root**.
```bash
pip install numpy matplotlib scipy
```
(`scipy` is used by `rq4_gate.py` / `rq4_analysis.py` for the reported p-values; without it those
scripts still run and print `p=n/a` instead of crashing.)

## Data
| File | What |
|---|---|
| `data/traj_data_v2_all89tasks.json` | all 1,794 annotations in one file (fail records have `t_commit`) |
| `data/v2_annotations/` | the same annotations, one JSON per trajectory (1,794 files) |
| `data/merged_tasks.json` | 89 tasks: `difficulty`, `category`, `task_type` |
| `data/pass_error_observability.json` | LLM-confirmed observability labels for PASS errors (Finding 11) |
| `data/case_studies_annotations.json` | full records for the case-study trajectories (Figs. 5–6) |
| `data/v1_annotations/` | the earlier v1 annotation round (`completed_traj_data*.json`, 355 + 826 records) and the v1↔v2 index files; used by `validation/codebook_history/` |

Raw trajectories (`merged_trajectories/`, 1,794 runs, ~780 MB) are not in this repository; they
are needed only to re-run the replay and the static checks, not to recompute any reported number.

**Field name ↔ paper terminology** (the JSON keeps the annotation-schema names):
`t_err` = $t_{err}$ · `t_commit` = $t_{lock}$ (failure lock-in) · `t_surface` = $t_{obs}$ (first observable).
A record is a **failure** iff it has `t_commit`. Trigger values map to Table II types
(`misread_output`→output misreading, `spec_neglect`→specification neglect,
`capability_limit`→capability limitation, `environment_obstacle_mishandled`→environment blocker).

Annotation schema & label definitions: **`docs/CODEBOOK.md`** (three timestamps, trigger
taxonomy, awareness, tail behavior, fabrication) — this is the specification the annotators and
the LLM-draft step followed. Oracle prompt: inside `scripts/build_oracle_batch.py`.

## Reproduce each result (run from package root)

| Paper artifact | Command | Output |
|---|---|---|
| **Dataset / Threats** (1794, 89 tasks, 16 cats, difficulty 459/742/593, medians) | `python scripts/corpus_stats.py` | stdout |
| **RQ1 F1–F3** ($t_{err}$/$t_{lock}$/$t_{obs}$ 7/12/16, fix window, 239) | `python scripts/rq1_analysis.py data/traj_data_v2_all89tasks.json` | `results/results_rq1.json`, `hazard.csv`, … |
| **Fig. 4** three-timestamp CDF | `python scripts/make_three_timepoints.py` | `figures/fig_three_timepoints.pdf` |
| **Fig. 5** RQ1 case (git-workflow) | `python scripts/make_rq1_case_v3.py` | `figures/RQ1_case_big.pdf` |
| **RQ1 F4** prefix-monitor oracle (18.2→28.8%) | *(regen needs raw prefixes; see note)* | `results/oracle_*.json`, `docs/oracle_VARIANTS.md` |
| **RQ2 Table II, F5–F6** (root-cause taxonomy, epistemic 57.9%) | `python scripts/rq23_analysis.py data/traj_data_v2_all89tasks.json` | `results/results_rq23.json` |
| **Fig. 6** RQ2 case (acl / sudo) | `python scripts/make_rq2_case_big.py` | `figures/RQ2_case_big.pdf` |
| **RQ3 Table III, F7–F8, F12** (5 regimes, fabrication) | `python scripts/rq23_analysis.py data/traj_data_v2_all89tasks.json` | `results/regimes.csv`, `results_rq23.json` |
| **RQ3 F9–F11** (71%, 5 vs 13, 92% vs 37%) | `python scripts/rq4_gate.py` | `results/results_rq4_gate.json`, `recovery_budget.csv` |
| **RQ4 Table IV & V, F13–F14** (pass grid 19–45%, epistemic 44–80%) | `python scripts/rq4_tables.py` | `results/table4_pass_grid.csv`, `table5_epistemic_grid.csv` |
| **Fig. 2** failed-trajectory distribution | `python scripts/make_failbar.py` | `figures/fig_failbar.pdf` |

`--boot`/`--vboot` control bootstrap iterations (defaults 10000/2000; lower for a quick run).

## Validation of the annotations (Section II-E/II-F, Table "replay")

| Paper artifact | Command (from `validation/replay/`) | Output |
|---|---|---|
| replay of 434 failed trajectories: 84.6% never objectively lock; t_err contradicted 21/434, t_lock contradicted 5/434; progress after t_lock 45/422 | `E4_RELAX_BASELINE=1 python3 scripts/e4_analyze.py runs inputs/census_sample.json inputs/pass_finals_all.json results/census_analysis.json` | `results/census_analysis.json` |
| contradiction table + consistency evidence | `python3 scripts/e4_validation_table.py results/census_analysis.json runs results/VALIDATION.md results/validation.json subtests` | `results/VALIDATION.md` |
| full census report (coverage, exclusions, per-task, fidelity strata) | `python3 scripts/e4_census_report.py results/census_analysis.json results/analysis.json inputs` | `results/CENSUS_REPORT.md` |
| static checks (t_surface 23.6% vs 28%, evidence quotes), codebook history, corpus-filter audit (hard 33.7% vs 17.8%, p = 0.017) | see `validation/README.md` §2–4 | `validation/static_checks/`, `codebook_history/`, `corpus_filtering/` |

The replay itself (Docker, Terminal-Bench images at commit `d28711d0`, raw trajectories) is
described in `validation/README.md`; the shipped `runs/` files are its complete output.


## License and citation
Scripts are released under the MIT License (`LICENSE`); the annotated dataset, validation
outputs, figures and documentation are released under CC BY 4.0 (`LICENSE-DATA`). You may use
either for any purpose; if you do, please cite the paper (BibTeX/APA via the "Cite this
repository" button on GitHub, metadata in `CITATION.cff`).
