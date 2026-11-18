# E4 sub-test calibration summary (43 tasks)

Excluded from replay (8): `create-bucket` (localstack ENTRYPOINT + in-memory bucket state not captured by docker commit), `mteb-eval` (image broken by dependency drift (transformers 5.x), oracle cannot run), `parallelize-graph` (oracle rebuilds Berkeley UPC (~10 min) per snapshot; cost prohibitive), `word2vec-from-scratch` (Dockerfile downloads HF dataset at build time; build fails on both hosts), `build-linux-kernel-qemu` (kernel build per snapshot is hours; oracle produces no bzImage under emulation), `mcmc-sampling-stan` (oracle cannot install rstan (cmake missing in image); 4x100k MCMC exceeds test timeout), `vul-flink` (oracle is a ~45 min networked maven build; per-snapshot cost prohibitive), `mteb-retrieve` (image broken by dependency drift (transformers 5.x); oracle exits 1 on pristine image)

| task | must | mustnot | untested | irreversibility | official pristine | official oracle (rc) |
|---|---|---|---|---|---|---|
| acl-permissions-inheritance | 5 | 2 | 1 | medium | 0/9 | 9/9 (0) |
| aimo-airline-departures | 4 | 0 | 0 | ? | 0/4 | 4/4 (0) |
| bank-trans-filter | 4 | 2 | 0 | ? | 0/1 | 1/1 (0) |
| build-cython-ext | 4 | 3 | 1 | medium | 1/11 | 10/11 (0) |
| build-linux-kernel-qemu * | 5 | 3 | 1 | high | 0/1 | 0/1 (0) |
| cancel-async-tasks | 5 | 2 | 1 | low | 0/6 | 6/6 (0) |
| configure-git-webserver | 4 | 2 | 1 | low | 0/1 | 1/1 (0) |
| count-dataset-tokens | 2 | 1 | 1 | low | 0/1 | 1/1 (0) |
| cpp-compatibility | 2 | 2 | 1 | ? | 1/2 | 2/2 (0) |
| create-bucket * | 2 | 2 | 0 | low | -/- | -/- (-) |
| distribution-search | 5 | 2 | 1 | low | 0/4 | 4/4 (0) |
| extract-elf | 5 | 3 | 1 | low | 0/2 | 2/2 (0) |
| fix-ocaml-gc | 4 | 2 | 1 | medium | 0/1 | 1/1 (0) |
| flood-monitoring-basic | 5 | 1 | 2 | high | 0/3 | 3/3 (0) |
| git-leak-recovery | 5 | 2 | 1 | high | 4/5 | 5/5 (0) |
| git-workflow-hack | 2 | 2 | 1 | low | 0/1 | 1/1 (0) |
| gomoku-planner | 5 | 1 | 1 | low | 0/3 | 3/3 (0) |
| heterogeneous-dates | 3 | 1 | 1 | low | 0/3 | 3/3 (0) |
| ilp-solver | 3 | 2 | 2 | low | 0/1 | 1/1 (0) |
| incompatible-python-fasttext | 3 | 3 | 1 | medium | 2/3 | None/None (None) |
| intrusion-detection | 5 | 2 | 2 | medium | 0/6 | 6/6 (0) |
| llm-inference-batching-scheduler | 6 | 2 | 2 | medium | 1/6 | 6/6 (0) |
| mahjong-winninghand | 4 | 2 | 2 | low | 0/2 | 2/2 (0) |
| mcmc-sampling-stan * | 5 | 2 | 3 | medium | 2/6 | 2/6 (1) |
| modernize-fortran-build | 5 | 2 | 1 | low | 0/3 | 3/3 (0) |
| mteb-eval * | 3 | 2 | 2 | low | 0/2 | 0/2 (1) |
| mteb-retrieve * | 4 | 2 | 1 | medium | 0/2 | 0/2 (1) |
| neuron-to-jaxley-conversion | 4 | 2 | 0 | high | 0/1 | 1/1 (0) |
| openssl-selfsigned-cert | 8 | 1 | 4 | low | 0/6 | 6/6 (0) |
| organization-json-generator | 5 | 1 | 3 | low | 0/4 | 4/4 (0) |
| pandas-etl | 6 | 3 | 2 | low | 0/3 | 3/3 (0) |
| parallelize-graph * | 6 | 2 | 1 | medium | 3/9 | 9/9 (0) |
| puzzle-solver | 5 | 2 | 1 | low | 2/15 | 15/15 (0) |
| query-optimize | 4 | 4 | 1 | low | 2/6 | 6/6 (0) |
| reshard-c4-data | 4 | 2 | 1 | medium | 0/1 | 1/1 (0) |
| schedule-vacation | 5 | 2 | 2 | low | 0/6 | 6/6 (0) |
| sqlite-db-truncate | 3 | 2 | 1 | high | 0/1 | 1/1 (0) |
| tmux-advanced-workflow | 2 | 2 | 1 | low | 4/5 | 5/5 (0) |
| train-fasttext | 4 | 1 | 1 | medium | 0/2 | 2/2 (0) |
| triton-interpret | 4 | 2 | 5 | medium | 0/6 | 6/6 (0) |
| vul-flask | 4 | 2 | 0 | medium | 1/3 | 3/3 (0) |
| vul-flink * | 4 | 3 | 1 | high | 0/1 | 1/1 (0) |
| word2vec-from-scratch * | 8 | 3 | 1 | medium | -/- | -/- (-) |

`*` = excluded from the replay batch.

## Reference-solution / official-test observations (verbatim from CALIBRATION.md files)

- **build-cython-ext**: **Observation for the paper: the reference solution does not satisfy the instruction's "tests/ … should still pass"
- **distribution-search**: Rule 1 ok (oracle passes all must/untested, violates no mustnot); rule 3 ok (5 must fail on pristine). Dropped: 0.
- **extract-elf**: Rule 1 (oracle passes all must/untested, violates no mustnot): ok. Rule 3 (pristine fails a must): ok (5/5 must fail).
- **extract-elf**: Observation: the official test never runs extract.js on /app/a.out (only on a freshly compiled new.o); the instruction's named binary is checked only here.
- **git-workflow-hack**: | test_must_about_me_page | dropped | oracle fails: solution.sh never builds the website |
- **git-workflow-hack**: | test_must_site_content_from_info_md | dropped | oracle fails: solution.sh never touches info.md content |
- **openssl-selfsigned-cert**: | test_mustnot_pem_world_readable | dropped | reference solution creates server.pem (which bundles the private key) with umask default 0644; oracle violates it. Key-only variant redundant with the must test. **Observation: the reference solution leaves the pri
- **organization-json-generator**: | test_untested_skill_distribution_and_average_years | untested | kept | schema-required statistics the official tests never check (skillDistribution, averageYearsOfService = 7.25) |
- **parallelize-graph**: | test_mustnot_input_test_file_modified | kept | md5 of /app/test (host). The oracle copies protected/test over it, but that file is byte-identical, so no violation |
- **parallelize-graph**: (pristine passes 3 official tests that are vacuous when outputs are missing; must-tests fail -> rule 3 holds.)
- **reshard-c4-data**: not install additional dependencies)". The reference solution violates this: no pyproject.toml, no venv; the official log shows
- **schedule-vacation**: Observation: the reference solution hard-codes Charlie's unavailable periods instead of parsing charlie_schedule.txt (the
- **tmux-advanced-workflow**: | test_must_output_csv_produced_by_fixed_script | **dropped** | reference solution waits 2 s per run while the script sleeps 5 s, then `tmux kill-session`s — its processing runs never finish and data/output.csv is never written (verified by running solution.sh
- **triton-interpret**: | test_mustnot_torch_or_numpy_calls_inside_kernels | kept (skip when no file) | step 8, static check: no `torch.`/`np.`/`numpy.` inside the body of any `@triton.jit` function (official test does a dynamic frame check that is easy to satisfy vacuously) |
- **vul-flink**: | test_must_no_tmp_success_left_by_official_probe | kept | acceptance criterion 1 as the official test phrases it; passes trivially on pristine (cluster never starts), which is why only 3/4 must fail there |
- **vul-flink**: | test_untested_normal_upload_still_works | kept | acceptance criterion 2 ("normal uploads continue to work") — the official test never performs a legitimate upload; checks POST /jars/upload with `e4_sub_normal.jar` returns 200 + `{"status":"success","filename

Totals: must 185, mustnot 86, untested 57 sub-tests across 43 tasks; 16 reference/official-test observations in 12 tasks.