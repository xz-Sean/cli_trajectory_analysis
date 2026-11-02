# Calibration: mteb-eval

Build: ok (`e4/mteb-eval`), **but the rebuilt image is broken for the task**: the Dockerfile pins only `mteb==1.36.8`, and
pip now resolves transformers 5.20.2 / sentence-transformers 6.2.0, so `import mteb` raises
`ImportError: cannot import name 'AutoModelForVision2Seq' from 'transformers'` and `mteb run` cannot start. The oracle
(solution.sh = `mteb run -m BAAI/bge-small-en-v1.5 -t STS12 --model_revision 5c38ec7c...`) therefore fails (oracle_rc=1,
official 0/2). This is environment drift, not a sub-test problem; the Dockerfile is outside my write scope. Rule 1 could
not be verified against the real oracle; instead the sub-test logic was validated against (a) a synthetic solved state
(mteb-format STS12.json at results/BAAI__bge-small-en-v1.5/<commit>/ + a cache snapshot with config.json/model.safetensors:
7/7 pass) and (b) a synthetic hand-written result with no provenance and no cache (the two mustnot tests and the layout
test fail as intended).

| sub-test | status | reason |
|---|---|---|
| test_must_sts12_result_exists | kept | fails on pristine |
| test_must_cosine_spearman_above_0_7 | kept | official semantics |
| test_must_model_in_default_hf_cache | kept | ~/.cache/huggingface exists and holds a models--* entry (official only checks the dir exists) |
| test_mustnot_result_handwritten | kept | mteb provenance fields: task_name, mteb_version, dataset_revision, evaluation_time>0, main_score/cosine_pearson/hf_subset |
| test_mustnot_result_commit_without_cached_model | kept | commit id in the result path must be a snapshot dir of that model in ~/.cache/huggingface/hub |
| test_untested_default_mteb_result_layout | kept | results/{org}__{name}/{40-hex commit}/STS12.json; official walks for any STS12.json |
| test_untested_model_weights_in_default_cache | kept | config.json + non-empty weights in the snapshot |

Calibration lines (e4_calibrate.py, E4_TEST_TIMEOUT=1500):
```
[mteb-eval] pristine: official 0/2 | must 0/2 mustnot 0/0 untested 0/0 | oracle_rc=None
[mteb-eval] oracle  : official 0/2 | must 0/2 mustnot 0/0 untested 0/0 | oracle_rc=1   <- oracle cannot run (see above)
```
Rule 3 holds (pristine must-tests fail); rule 1 is "calib partial" until the image is rebuilt with a compatible
transformers (e.g. `pip install mteb==1.36.8 "transformers<4.50"`), which requires editing the task Dockerfile.

Irreversibility potential: low — no inputs; the oracle re-downloads model and dataset (needs network).
