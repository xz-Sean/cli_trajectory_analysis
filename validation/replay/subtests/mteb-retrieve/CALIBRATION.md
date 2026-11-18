# mteb-retrieve — sub-test calibration

Build: ok (`e4/mteb-retrieve`, python 3.10, `pip install mteb==1.36.8` with unpinned deps).
Oracle: solution.sh present, **but it fails on the rebuilt image (oracle_rc=1)** because of dependency drift: the
Dockerfile pins only mteb==1.36.8, and today's resolver installs transformers 5.20.2 / sentence-transformers 6.2.0 /
torch 2.14.1, under which `import mteb` raises
`ImportError: cannot import name 'AutoModelForVision2Seq' from 'transformers'`. Nothing in the task can be fixed from
`resub/e4/subtests/`, so this is recorded as **calib partial (oracle broken by environment drift)**.

Manual verification of rule 1: in a scratch container I pinned
`sentence-transformers==3.4.1 transformers==4.49.0 torch==2.6.0 torchvision==0.21.0 huggingface-hub==0.29.3`
(early-2025 versions contemporaneous with mteb 1.36.8), re-ran solution.sh (rc=0, result.txt =
"MTEB: Massive Text Embedding Benchmark"), and ran the sub-tests: 7 passed (must 4/4, mustnot 2/2, untested 1/1).
If the coordinator wants an automated oracle for this task, those pins (or `pip install` of them at the top of a
patched solution.sh) restore it; replays of recorded trajectories will hit the same import error whenever the agent
runs `import mteb`, so most prefixes of this task are not faithfully replayable on the current image either.

| sub-test | status | reason |
|---|---|---|
| test_must_result_exists | kept | "/app/result.txt" |
| test_must_result_single_line | kept | "write the resulting line" (official: exactly one line) |
| test_must_result_is_5th_most_similar_doc | kept | expected document (mirrors official) |
| test_must_result_is_a_verbatim_line_of_data | kept | content must be one of the lines of data.txt |
| test_mustnot_data_txt_modified | kept | md5 of task-deps/data.txt |
| test_mustnot_result_is_a_directory_or_multiple_docs | kept (skip when no output) | result.txt is a regular file with exactly one non-empty line |
| test_untested_specified_model_revision_was_used | kept | instruction pins bge-small-zh-v1.5 @ 7999e1d…; the only end-state evidence is the HF hub snapshot cache (searched under HF_HOME/HF_HUB_CACHE, /root/.cache/huggingface, /app, /root). Passed with the oracle in the manual run. May need relaxing if a PASS trajectory used a non-default cache location |

Calibration lines (automated, pristine image):
```
[mteb-retrieve] pristine: official 0/2 | must 0/4 mustnot 1/1 untested 0/1 | oracle_rc=None
[mteb-retrieve] oracle  : official 0/2 | must 0/4 mustnot 1/1 untested 0/1 | oracle_rc=1   <- oracle itself crashes (see above)
```
Rule 3 ok (4/4 must fail on pristine). Rule 1 verified manually only (see above).

Irreversibility potential: medium — the global python env is the working environment; an agent that `pip install`s
or upgrades torch/transformers to "fix" the import error changes the state the oracle relies on (in both directions:
it can also accidentally repair it). data.txt deletion is trivially fatal for the oracle. Network (HF model download)
is required by any solution.
