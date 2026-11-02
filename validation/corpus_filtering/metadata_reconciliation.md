# E7 metadata reconciliation (89 paper tasks)

Sources: (A) `task.yaml` from the pinned Terminal-Bench checkout (`resub/tb_tasks/TB_COMMIT.txt`), (B) `merged_tasks.json` (the paper's task table), (C) `terminal_bench_task_stats.md` (older local 241-task table).

Coverage of the 89 tasks: {'pinned_task_yaml': 89, 'merged_tasks.json': 89, 'task_stats.md': 89}

## Pairwise disagreement counts (89 tasks)

| comparison | raw | after category normalisation (game->games, math->mathematics, file_operations->file-operations) |
|---|---|---|
| pinned_task_yaml vs merged_tasks.json / category | 11 | 11 |
| pinned_task_yaml vs merged_tasks.json / difficulty | 0 | 0 |
| pinned_task_yaml vs task_stats.md / category | 48 | 48 |
| pinned_task_yaml vs task_stats.md / difficulty | 38 | 38 |
| merged_tasks.json vs task_stats.md / category | 53 | 53 |
| merged_tasks.json vs task_stats.md / difficulty | 38 | 38 |

## Every disagreement (any source differs)

| task | field | pinned task.yaml | merged_tasks.json | task_stats.md |
|---|---|---|---|---|
| audio-synth-stft-peaks | category | scientific-computing | scientific-computing | audio-processing |
| bank-trans-filter | category | data-science | data-science | data-processing |
| build-cython-ext | category | debugging | debugging | software-engineering |
| build-cython-ext | difficulty | medium | medium | easy |
| build-linux-kernel-qemu | difficulty | medium | medium | hard |
| cancel-async-tasks | difficulty | hard | hard | easy |
| chem-rf | category | model-training | model-training | scientific-computing |
| chem-rf | difficulty | hard | hard | medium |
| configure-git-webserver | difficulty | hard | hard | medium |
| constraints-scheduling | category | personal-assistant | personal-assistant | algorithms |
| count-call-stack | category | system-administration | system-administration | debugging |
| count-call-stack | difficulty | easy | easy | medium |
| count-dataset-tokens | category | model-training | model-training | data-processing |
| count-dataset-tokens | difficulty | medium | medium | easy |
| cpp-compatibility | category | debugging | debugging | software-engineering |
| create-bucket | category | file-operations | file-operations | system-administration |
| cross-entropy-method | category | software-engineering | software-engineering | scientific-computing |
| cross-entropy-method | difficulty | easy | easy | medium |
| csv-to-parquet | category | data-science | data-science | data-processing |
| db-wal-recovery | category | file-operations | file-operations | data-science |
| distribution-search | category | machine-learning | machine-learning | data-science |
| distribution-search | difficulty | medium | medium | easy |
| extract-elf | category | file-operations | file-operations | security |
| extract-moves-from-video | category | file-operations | file-operations | data-science |
| extract-moves-from-video | difficulty | hard | hard | medium |
| filter-js-from-html | category | security | security | file-operations |
| filter-js-from-html | difficulty | medium | medium | easy |
| find-official-code | category | research | data-science | research |
| find-official-code | difficulty | hard | hard | easy |
| fix-ocaml-gc | category | software-engineering | software-engineering | debugging |
| flood-monitoring-basic | category | data-processing | data-science | data-science |
| git-leak-recovery | category | software-engineering | software-engineering | security |
| git-multibranch | category | system-administration | system-administration | software-engineering |
| git-workflow-hack | category | security | security | software-engineering |
| git-workflow-hack | difficulty | easy | easy | medium |
| gomoku-planner | category | game | game-ai | game |
| gpt2-codegolf | category | software-engineering | software-engineering | model-training |
| gpt2-codegolf | difficulty | hard | hard | medium |
| hello-world | category | file-operations | system-administration | file-operations |
| heterogeneous-dates | category | file-operations | file-operations | data-processing |
| ilp-solver | difficulty | easy | easy | medium |
| intrusion-detection | category | system-administration | system-administration | security |
| leelachess0-pytorch-conversion | category | machine-learning | machine-learning | model-training |
| mahjong-winninghand | category | games | games | algorithms |
| mahjong-winninghand | difficulty | easy | easy | medium |
| mcmc-sampling-stan | category | data-science | data-science | scientific-computing |
| mcmc-sampling-stan | difficulty | hard | hard | medium |
| mlflow-register | category | data-science | data-science | model-training |
| modernize-fortran-build | difficulty | easy | easy | medium |
| movie-helper | category | mathematics | mathematics | data-science |
| movie-helper | difficulty | hard | hard | easy |
| mteb-eval | category | data-science | data-science | machine-learning |
| mteb-leaderboard | category | data-science | data-science | machine-learning |
| mteb-leaderboard | difficulty | medium | medium | easy |
| mteb-retrieve | category | data-science | data-science | machine-learning |
| mteb-retrieve | difficulty | medium | medium | easy |
| multi-source-data-merger | category | data-processing | data-processing | data-science |
| openssl-selfsigned-cert | difficulty | medium | medium | easy |
| organization-json-generator | category | file-operations | file-operations | data-processing |
| organization-json-generator | difficulty | hard | hard | medium |
| parallelize-graph | category | scientific-computing | scientific-computing | software-engineering |
| parallelize-graph | difficulty | hard | hard | easy |
| play-zork-easy | difficulty | hard | hard | medium |
| protein-assembly | difficulty | hard | hard | medium |
| puzzle-solver | category | algorithms | algorithms | file-operations |
| query-optimize | category | data-science | data-science | data-querying |
| rare-mineral-allocation | difficulty | hard | hard | medium |
| recover-obfuscated-files | difficulty | easy | easy | medium |
| regex-chess | category | software-engineering | software-engineering | games |
| reshard-c4-data | category | data-science | data-science | data-processing |
| sam-cell-seg | category | data-science | data-science | computer-vision |
| sam-cell-seg | difficulty | hard | hard | medium |
| schedule-vacation | category | algorithms | algorithms | file-operations |
| setup-custom-dev-env | category | software-engineering | software-engineering | system-administration |
| solve-maze-challenge | category | algorithms | game-ai | algorithms |
| solve-maze-challenge | difficulty | medium | medium | hard |
| speech-to-text | category | audio-processing | data-science | machine-learning |
| spinning-up-rl | category | machine-learning | model-training | model-training |
| spinning-up-rl | difficulty | easy | easy | hard |
| sqlite-db-truncate | category | debugging | data-science | debugging |
| stable-parallel-kmeans | category | machine-learning | data-science | machine-learning |
| stable-parallel-kmeans | difficulty | hard | hard | medium |
| tmux-advanced-workflow | category | debugging | software-engineering | system-administration |
| tmux-advanced-workflow | difficulty | medium | medium | easy |
| train-fasttext | difficulty | hard | hard | easy |
| triton-interpret | category | model-training | model-training | software-engineering |
| vertex-solver | difficulty | medium | medium | hard |
| video-processing | category | video-processing | software-engineering | video-processing |
| video-processing | difficulty | hard | hard | medium |
| vul-flask | difficulty | medium | medium | easy |
| winning-avg-corewars | category | software-engineering | software-engineering | games |
| winning-avg-corewars | difficulty | medium | medium | hard |
| word2vec-from-scratch | category | model-training | model-training | scientific-computing |

Total disagreement rows: 93 (55 category, 38 difficulty).

## Which source do the paper's numbers correspond to?

### Distinct categories among the 89 tasks

| source | distinct (raw) | distinct (normalised) |
|---|---|---|
| pinned_task_yaml | 19 | 18 |
| merged_tasks.json | 16 | 16 |
| task_stats.md | 20 | 19 |

Paper claims 16 categories.

- pinned_task_yaml: software-engineering (16), data-science (11), system-administration (8), model-training (8), file-operations (7), security (6), mathematics (5), debugging (5), machine-learning (5), scientific-computing (4), games (3), algorithms (3), data-processing (2), personal-assistant (1), research (1), game (1), optimization (1), audio-processing (1), video-processing (1)
- merged_tasks.json: software-engineering (18), data-science (16), system-administration (9), model-training (9), file-operations (6), security (6), mathematics (5), scientific-computing (4), debugging (3), games (3), machine-learning (3), game-ai (2), algorithms (2), personal-assistant (1), data-processing (1), optimization (1)
- task_stats.md: software-engineering (15), system-administration (8), model-training (8), data-science (7), security (7), data-processing (6), scientific-computing (6), machine-learning (6), mathematics (4), games (4), debugging (4), file-operations (4), algorithms (3), audio-processing (1), research (1), game (1), optimization (1), data-querying (1), computer-vision (1), video-processing (1)

### Task-level difficulty of the 89 tasks

| source | easy | medium | hard | other |
|---|---|---|---|---|
| pinned_task_yaml | 22 | 37 | 30 |  |
| merged_tasks.json | 22 | 37 | 30 |  |
| task_stats.md | 28 | 43 | 18 |  |

### Trajectory-level difficulty over the 1794 analysed records (paper: 459 easy / 742 medium / 593 hard)

| source | easy | medium | hard | other | matches paper |
|---|---|---|---|---|---|
| pinned_task_yaml | 459 | 742 | 593 |  | YES |
| merged_tasks.json | 459 | 742 | 593 |  | YES |
| task_stats.md | 584 | 867 | 343 |  | no |

Split by outcome (FAIL = record has `t_err`):

| source | easy F/P | medium F/P | hard F/P |
|---|---|---|---|
| pinned_task_yaml | 150/309 | 517/225 | 517/76 |
| merged_tasks.json | 150/309 | 517/225 | 517/76 |
| task_stats.md | 322/262 | 558/309 | 304/39 |

How difficulty is determined: it is the `difficulty` field that each task author wrote in `task.yaml` (values easy/medium/hard; no rubric is enforced by the benchmark). The paper's trajectory-level counts simply attach each task's label to every one of its analysed trajectories.

## Sanity check on `terminal_bench_task_stats.md` (all tasks)

Its per-task table has 241 rows, 241 in common with the pinned checkout; it disagrees with the pinned task.yaml on category for 118 and on difficulty for 107 of them. The header tables of that file (difficulty 64 easy / 120 medium / 57 hard; category counts) equal the pinned checkout's marginals ({'hard': 57, 'easy': 64, 'medium': 120}), but the marginals of its own per-task table are {'hard': 49, 'easy': 71, 'medium': 121}, i.e. the per-task table is inconsistent with the file's own header. The per-task rows therefore do not reflect any version of the benchmark's task.yaml files and must not be used as a metadata source; the pinned task.yaml is authoritative.

