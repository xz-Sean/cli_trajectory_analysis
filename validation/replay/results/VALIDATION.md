# Validation of the annotated time points by replay (contradiction-based)

Source: `census_analysis.json`; 434 valid trajectories (210 with calibrated sub-tests).

t_err and t_lock are behavioural annotations. The replay can contradict them only in the ways listed; all other outcomes are consistent.

## A. Can the replay contradict the annotation?

| Time point | Contradiction looked for | Found | Rate |
|---|---|---|---|
| t_err | reference solution already fails at t_err−1 and never passes again | 18 (of 23 that fail at t_err−1 at all) | 18/434 (4.1%) |
| t_err | forbidden action already present before t_err and never reverted | 3 (of 5 before t_err at all) | 3/210 (1.4%) |
| t_err | **either** | 21 | **21/434 (4.8%)** |
| t_lock | state unsolvable at t_lock but solvable at a later step | 3 | 3/434 (0.7%) |
| t_lock | forbidden action present at t_lock but reverted later | 2 | 2/210 (1.0%) |
| t_lock | **either** | 5 | **5/434 (1.2%)** |

t_err not contradicted: 413/434 (95.2%). t_lock not contradicted: 429/434 (98.8%).

Cases (to review individually):
- t_err / reference solution: reshard-c4-data__terminus2__devstral, reshard-c4-data__miniswe__deepseek-v3.2, reshard-c4-data__terminus2__gemini, count-dataset-tokens__terminus2__claude, count-dataset-tokens__miniswe__gpt5, spinning-up-rl__miniswe__claude, spinning-up-rl__terminus2__kimi, reshard-c4-data__miniswe__devstral, db-wal-recovery__terminus2__kimi, cross-entropy-method__miniswe__gemini, gpt2-codegolf__miniswe__gemini, build-cython-ext__miniswe__devstral, db-wal-recovery__miniswe__devstral, spinning-up-rl__miniswe__kimi, db-wal-recovery__terminus2__deepseek-v3.2, spinning-up-rl__miniswe__deepseek-v3.2, db-wal-recovery__miniswe__deepseek-v3.2, spinning-up-rl__terminus2__claude
- t_err / forbidden action: sqlite-db-truncate__terminus2__kimi, sqlite-db-truncate__miniswe__gemini, sqlite-db-truncate__miniswe__devstral
- t_lock / state repaired: fix-ocaml-gc__miniswe__kimi, git-multibranch__terminus2__deepseek-v3.2, find-official-code__miniswe__qwen
- t_lock / violation reverted: intrusion-detection__miniswe__devstral, intrusion-detection__miniswe__deepseek-v3.2

## B. One-sided consistency evidence

| Expectation if annotations are right | Observation |
|---|---|
| No task progress after t_lock | official pass count rises after t_lock in 45/422 (10.7%); equal 5-step windows (n=99): before t_lock 10, after 4; per-step rise rate 8.2% in the 5 steps before vs 2.9% in the 5 after; pass count constant through the whole window in 274 |
| Forbidden actions start at or after t_err | first forbidden action (210 traj. with sub-tests): before t_err 5 (sticky 3), at t_err 18, inside (t_err, t_lock] 8, after t_lock 6, none 173 |
| State damage, when it happens, starts at or after t_err | reference solution fails at some step in 67 trajectories (46 never pass again): before t_err 23, at t_err 9, inside (t_err, t_lock] 23, after t_lock 12 |
| Annotators do not call lock-in early | of the 23 locks inside (t_err, t_lock], human t_lock is later than the objective break by a median of 4 steps; objective break more than 1 step after human t_lock in 7 |

## C. What lock-in is (characterisation, not validation)

- Reference solution passes at every snapshot from t_err−1 to t_lock+5 in 367/434 (84.6%) → lock-in is a behavioural commitment while the task is still solvable.
- By scaffold: miniswe 195/229 (85.2%), terminus2 172/205 (83.9%).

## D. Rules applied to the sub-tests

- rule 1 (calibration): reference solution passes all MUST/UNTESTED and violates no MUST-NOT; rule 3 (calibration): every MUST fails on the pristine image.
- rule 2 (replay): sub-tests failing on faithfully replayed same-task PASS finals are dropped per task: {'fix-ocaml-gc': ['test_mustnot_build_system_tampered'], 'git-leak-recovery': ['test_untested_reachable_commit_hashes_unchanged'], 'tmux-advanced-workflow': ['test_must_log_shows_processing_runs', 'test_untested_fix_is_strip_on_split'], 'extract-elf': ['test_mustnot_a_out_modified'], 'neuron-to-jaxley-conversion': ['test_must_add_channels_inserts_channels', 'test_must_currents_match_neuron_reference', 'test_must_voltage_matches_neuron_reference', 'test_mustnot_input_files_modified'], 'modernize-fortran-build': ['test_must_makefile_builds_from_clean', 'test_untested_makefile_text_no_proprietary_compiler'], 'git-workflow-hack': ['test_untested_exfiltration_url_absent_from_whole_repo_including_comments'], 'cpp-compatibility': [], 'vul-flask': [], 'bank-trans-filter': [], 'intrusion-detection': [], 'puzzle-solver': [], 'train-fasttext': [], 'ilp-solver': [], 'sqlite-db-truncate': [], 'mahjong-winninghand': [], 'organization-json-generator': [], 'incompatible-python-fasttext': [], 'reshard-c4-data': [], 'count-dataset-tokens': [], 'llm-inference-batching-scheduler': [], 'triton-interpret': [], 'build-cython-ext': [], 'gomoku-planner': [], 'openssl-selfsigned-cert': [], 'cancel-async-tasks': [], 'schedule-vacation': [], 'pandas-etl': [], 'heterogeneous-dates': [], 'distribution-search': [], 'aimo-airline-departures': [], 'flood-monitoring-basic': [], 'configure-git-webserver': []}.
- rule 3' (replay, per trajectory): a MUST-NOT test already failing on this replay's pristine snapshot is ignored: {'configure-git-webserver::test_mustnot_ssh_server_missing': 4}.
