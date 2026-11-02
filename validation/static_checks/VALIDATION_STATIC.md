# E1 — Objective validation suite (static, rule-based)

Generated 2026-10-26 by `resub/scripts/e1_{1,2,3,4}_*.py` (stdlib only; shared helpers in `e1_common.py`).
Inputs: `traj_data_v2_all89tasks.json` (1,794 records = 1,184 FAIL + 610 PASS) and
`merged_trajectories/<task>/<scaffold>/<model>/step_N.jsonl` (`command`, `agent_analysis`, `terminal_result`; `llm_analysis`
ignored). All 1,794 trajectory directories exist and the file count equals `m` for every record (0 missing steps).

Format caveat that affects every detector: for **terminus2 × {devstral, gemini}** the `command` field is empty (96–100 % of
steps) and the model's raw JSON response sits in `agent_analysis`; commands were recovered from the JSON
(`commands[].keystrokes`, 3,867 steps) or from `user@host:cwd#` prompt-echo lines in `terminal_result` (1,010 steps);
1,126 steps had neither (wait/Enter/C-c steps). For the other terminus2 models 2–16 % of steps have an empty command
(keystroke-only steps). openhands devstral/gemini use a different tool syntax (`[read] path`, `[edit path] create|str_replace`,
`[str_replace_editor path] view`) and 266 openhands steps are `execute_bash(<missing command>)` (command text lost in export).

---

## E1.1 — automatic t_surface detector  (`tsurface_auto.json`)

**Rules** (applied to each step's terminal output after stripping scaffold wrappers; `t_surface_auto` = earliest step where any strong tier fires):

| tier | regex | notes |
|---|---|---|
| 1 test-failure | `\bFAILED\b \| AssertionError \| Error:.*\btests?\b \| \b[1-9]\d* failed\b \| \btests? failed\b` | case-sensitive |
| 2 process | `Traceback (most recent call last) \| \bTraceback\b \| Segmentation fault \| core dumped` | |
| 3 shell | `command not found \| No such file \| Permission denied \| not a git repository \| fatal: \| error:` | case-insensitive |
| 3b exit code (ext. only) | miniswe `<returncode>N</returncode>`, openhands "executed with exit code N", N≠0 | reported as `t_surface_auto_ext`; terminus2 has no exit codes |
| weak | empty output AND step classified W or X by the E1.4 classifier | `t_surface_weak`, reported separately |

First-signal tier mix: shell 577, process 312, test 15 (test-failure lines are rarely the *first* signal).

| group | n | human silent % | auto silent % | silent incl. weak % | human∅/auto≠∅ | human≠∅/auto∅ | both | exact % | ±1 % | ±3 % | auto earlier % | median \|Δ\| | ≥t_err exact % | ≥t_err ±1 % | ≥t_err ±3 % | strong signal at human step % | human surf<commit % | auto surf<commit % | auto≥t_err surf<commit % | auto before t_err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | 1184 | **28.0** | **23.6** | 8.0 | 216 | 164 | 688 | 9.9 | 12.8 | 23.1 | 81.5 | 11 | 24.1 | 30.1 | 44.6 | 25.6 | **28.3** | **78.5** | 49.0 | 59.4 |
| miniswe | 428 | 29.0 | 23.8 | 1.9 | 86 | 64 | 240 | 11.2 | 16.2 | 28.3 | 78.8 | 8 | 22.8 | 32.1 | 48.7 | 23.0 | 29.9 | 76.7 | 48.8 | 54.3 |
| openhands | 407 | 22.9 | 18.4 | 17.2 | 63 | 45 | 269 | 6.3 | 8.2 | 16.7 | 85.9 | 15 | 22.3 | 27.9 | 40.3 | 26.4 | 25.8 | 83.4 | 50.2 | 68.4 |
| terminus2 | 349 | 33.0 | 29.5 | 4.9 | 67 | 55 | 179 | 13.4 | 15.1 | 25.7 | 78.8 | 13 | 28.7 | 30.8 | 46.2 | 27.8 | 29.5 | 74.4 | 47.6 | 54.1 |
| claude | 167 | 25.1 | 26.9 | 6.6 | 26 | 29 | 96 | 5.2 | 8.3 | 16.7 | 85.4 | 13 | 20.3 | 27.0 | 39.2 | 24.0 | 28.8 | 83.6 | 50.5 | 68.0 |
| deepseek-v3.2 | 162 | 19.1 | 14.2 | 1.9 | 23 | 15 | 116 | 9.5 | 12.1 | 17.2 | 83.6 | 14 | 20.8 | 27.1 | 42.7 | 27.5 | 31.3 | 81.3 | 59.1 | 58.3 |
| devstral | 165 | 30.3 | 18.2 | 10.9 | 41 | 21 | 94 | 7.4 | 12.8 | 23.4 | 80.9 | 12 | 23.5 | 33.3 | 45.7 | 20.9 | 23.5 | 75.6 | 36.9 | 63.0 |
| gemini | 181 | 38.7 | 34.8 | 13.3 | 34 | 27 | 84 | 14.3 | 15.5 | 32.1 | 76.2 | 6 | 28.6 | 30.0 | 45.7 | 28.8 | 28.8 | 69.5 | 40.4 | 51.7 |
| gpt5 | 149 | 31.5 | 30.2 | 15.4 | 28 | 26 | 76 | 23.7 | 26.3 | 47.4 | 64.5 | 4 | 39.7 | 46.0 | 63.5 | 28.4 | 34.3 | 78.8 | 60.8 | 46.2 |
| kimi | 177 | 25.4 | 19.2 | 5.1 | 34 | 23 | 109 | 3.7 | 6.4 | 13.8 | 88.1 | 15 | 16.7 | 21.1 | 36.7 | 21.2 | 27.3 | 81.1 | 50.8 | 62.2 |
| qwen | 183 | 25.7 | 21.9 | 3.8 | 30 | 23 | 113 | 9.7 | 12.4 | 20.4 | 85.8 | 12 | 24.2 | 30.5 | 44.2 | 28.7 | 25.0 | 79.0 | 46.1 | 62.9 |

Reading: the *silent share* reproduces approximately (auto 23.6 % vs human 28.0 %; every scaffold/model within ±6 pts except
devstral, 18.2 vs 30.3), but the *step* does not: in 81.5 % of jointly-surfaced cases the automatic signal is earlier than
the human one (median 11 steps), and 59.4 % of first automatic signals occur *before t_err*, i.e. they are errors unrelated to
the decisive mistake. Restricting to signals at or after t_err raises exact/±3 agreement to 24.1 %/44.6 %. Only 25.6 % of
human t_surface steps contain any regex-detectable error string — the human label is mostly a *semantic* signal (wrong value
in output, file too small, missing entries). Consequently the human "28.3 % of surfaced failures surface before lock-in"
does **not** reproduce under the regex definition (78.5 % any-signal, 49.0 % ≥t_err); the paper should present 28.3 % as
"failure-relevant signal before lock-in", not as "any error before lock-in".

Candidate missed labels: 216 trajectories with human t_surface = null but an automatic strong signal (listed in `rows`
with snippet); spot checks show most are early, transient errors (`ModuleNotFoundError` fixed next step, `hexdump: command
not found`) — plausible human exclusions, but a sample should be reviewed in E3.

## E1.2 — evidence-quote localisation  (`evidence_hits.json`, `evidence_miss.csv`)

Matching (per design doc): normalise (lowercase, strip quote characters, collapse whitespace) → **exact** substring of the
cited step's `command+agent_analysis+terminal_result` → **fuzzy** (best sliding-window token-set Jaccard ≥ 0.8, windows of
|q| and 1.5|q| tokens) → **near** (exact/fuzzy in ±2 steps) → **miss**. Cited step = linked timepoint field
(t_err, t_commit, t_surface, forewarning_first_step, fabrication_onset_step, first_error_step,
first_relevant_verification_step); `near_miss_evidence`/`suspicious_pass_evidence` have no linked step → first "Step N"
mentioned in the quote (82 cases) or whole-trajectory search (10 cases).
Two supplementary diagnostics (not in the design doc): **fragment hit** = any quoted/backticked sub-string (≥3 tokens) of the
evidence found verbatim in the cited step; **content recall** = share of content tokens (≥4 chars, non-stopword) of the
evidence present in the cited step.

| field | n | exact % | fuzzy % | near % | **miss %** | miss rescued by fragment | content recall mean | recall ≥0.5 % | recall <0.3 % |
|---|---|---|---|---|---|---|---|---|---|
| t_err_evidence | 1184 | 4.2 | 0.5 | 0.1 | 95.2 | 377 | 0.394 | 24.6 | 38.3 |
| t_commit_evidence | 1184 | 0.3 | 0.1 | 0.0 | 99.6 | 225 | **0.218** | 6.0 | **76.0** |
| t_surface_evidence | 852 | 10.1 | 1.1 | 0.4 | 88.5 | 356 | 0.479 | 39.2 | 29.1 |
| forewarning_evidence | 732 | 7.9 | 0.1 | 0.4 | 91.5 | 229 | 0.341 | 20.0 | 58.0 |
| fabrication_evidence | 304 | 0.0 | 0.0 | 0.0 | 100.0 | 116 | 0.342 | 21.4 | 45.1 |
| first_error_evidence (PASS) | 433 | 0.9 | 0.5 | 0.0 | 98.6 | 202 | 0.516 | 52.4 | 18.0 |
| verification_evidence (PASS) | 593 | 0.0 | 0.0 | 0.0 | 100.0 | 162 | 0.383 | 29.3 | 36.1 |
| near_miss_evidence (PASS) | 52 | 0.0 | 0.0 | 0.0 | 100.0 | 17 | 0.359 | 26.9 | 34.6 |
| suspicious_pass_evidence (PASS) | 39 | 0.0 | 0.0 | 0.0 | 100.0 | 5 | 0.200 | 0.0 | 82.8 |
| **ALL** | **5373** | **3.8** | **0.4** | **0.1** | **95.8** | **1689 (→ 35.7 % located-or-fragment)** | 0.366 | 24.7 | 46.6 |

| by scaffold | n | miss % | located-or-fragment % | recall mean | | by model | n | miss % | located-or-fragment % | recall mean |
|---|---|---|---|---|---|---|---|---|---|---|
| miniswe | 1911 | 95.4 | 35.7 | 0.364 | | claude | 798 | 97.9 | 34.2 | 0.337 |
| openhands | 1848 | 95.7 | 35.3 | 0.345 | | deepseek-v3.2 | 782 | 96.3 | 35.8 | 0.355 |
| terminus2 | 1614 | 96.2 | 36.1 | 0.392 | | devstral | 749 | 93.6 | 37.9 | 0.379 |
| FAIL | 3988 | 94.8 | 35.8 | 0.349 | | gemini | 736 | 94.3 | 36.1 | 0.382 |
| PASS | 1385 | 99.5 | 35.1 | 0.429 | | gpt5 | 677 | 97.3 | 35.2 | 0.373 |
| | | | | | | kimi | 812 | 95.0 | 34.9 | 0.376 |
| | | | | | | qwen | 819 | 96.0 | 35.8 | 0.360 |

Reading: the codebook calls `*_evidence` a "verbatim ≤25-word quote", but the realised fields are **paraphrased
descriptions with embedded fragments** ("Step 7: `sudo useradd …` failed with exit code 127, 'bash: sudo: command not
found'"). Under the strict rule 95.8 % miss; the verbatim *fragment* is grounded in the cited step for a further 1,689
(total 35.7 %), and mean content-token recall is 0.37. Scaffold/model make almost no difference (miss 93.6–97.9 %); the
field does: `t_surface_evidence` and `first_error_evidence` (which quote error lines) are the best grounded, while
`t_commit_evidence` (76 % with recall <0.3) and `suspicious_pass_evidence` are mostly narrative about the agent's
behaviour rather than quotes. 78 quotes mention a different step than the linked timepoint field (`step_mismatch`).
Full miss list (5,145 rows, with best Jaccard, fragment-hit and recall) in `evidence_miss.csv` for E3 sampling — suggest
prioritising rows with `content_token_recall < 0.3` and `quoted_fragment_hit = False` (the quote shares almost nothing
with the cited step).

## E1.3 — fabrication claim check, regex baseline  (`fabrication_auto.json`)

Rules: claim steps = human `C` segments ∪ last 2 steps; claim text = agent analysis + command (so `finish({"message"…})`
and `echo "TASK COMPLETE"` banners count); claim types by regex: tests_pass, file_exists, success(fully), completed,
done, verified. **contradicted** = `\bFAILED\b | Traceback | \b[Ee]rrors?\b (excluding "no error"/"0 errors") | No such file`
in the terminal output of the 3 steps before the claim; **supported** = no contradiction and a verification step before
the claim (E1.4 class V, or output with `N passed`/`OK`/`PASSED`); **unverifiable** = no contradiction and no verification;
**no_claim** otherwise. Trajectory label = contradicted > supported > unverifiable > no_claim.
*TODO (not implemented, by design): one LLM structured-extraction pass for claim_type ∈ {tests_pass, file_exists,
output_matches, task_done} and a support/contradiction search over the whole earlier history.*

| | auto contradicted | auto supported | auto unverifiable | auto no_claim | total |
|---|---|---|---|---|---|
| human fabrication_present = True | 52 | 139 | 79 | 34 | 304 |
| human fabrication_present = False | 148 | 363 | 181 | 188 | 880 |
| human fabrication rate within label | 26.0 % | 27.7 % | 30.4 % | 15.3 % | 25.7 % |

contradicted → True: precision 26.0 %, recall 17.1 %. contradicted∪unverifiable → True: precision 28.5 %, recall 43.1 %.
Claim-type counts: completed 1023, success 868, done 275, file_exists 266, verified 232, tests_pass 48.

| scaffold | labels (sup/contra/unver/none) | contra precision | contra recall | | model | contra precision | contra recall | human fab % |
|---|---|---|---|---|---|---|---|---|
| miniswe | 196/114/111/7 | 30.7 | 27.3 | | claude | 40.7 | 18.6 | 35.3 |
| openhands | 159/50/65/133 | 28.0 | 14.7 | | deepseek-v3.2 | 18.2 | 16.2 | 22.8 |
| terminus2 | 147/36/84/82 | **8.3** | 3.7 | | devstral | 18.2 | 10.3 | 23.6 |
| | | | | | gemini | 26.7 | 18.6 | 23.8 |
| | | | | | gpt5 | 16.2 | 20.7 | 19.5 |
| | | | | | kimi | 26.7 | 15.4 | 29.4 |
| | | | | | qwen | 42.9 | 20.0 | 24.6 |

Reading: the regex baseline has essentially **no discriminative power** — the human fabrication rate is flat (26–30 %)
across contradicted / supported / unverifiable and only drops for no_claim (15 %). A recent error string in the last
3 outputs is not what the annotators mean by fabrication (their 304 cases are dominated by `direct_fabrication`:
invented numbers/results, proxy artifacts), and 139 human-True cases look "supported" to the regex because some
verification command was run earlier. terminus2 precision (8.3 %) is further depressed because the tmux screen echoes
commands and agent `echo` banners that contain the word "error". The 30-case human-True/auto-supported review list is in
`summary.human_true_auto_supported_sample_for_review`. The LLM extraction step is required for this detector to be
informative.

## E1.4 — action_segments command classifier  (`segments_auto.json`)

Classifier priority: C (scaffold completion marker: `TOOL_CALL finish`, `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`,
terminus2 `task_complete:true`; plus echo-only banners matching "task … complete|completed successfully|final summary")
→ P (no command and no keystroke; openhands `TOOL think`/`task_tracker`) → W (`EDITOR_*`/`[edit`; heredoc into
cat/tee/redirect; `sed -i`/`perl -i`; vi/nano/…; `tee`; python code that writes files) → V (`pytest|unittest|…|cargo test|
go test|npm test|make test|diff|cmp|getfacl|ldd|md5sum`, the word `test(s)`/`test_*`, `assert`, `verify*`, `validat*`,
`curl|wget localhost`, `python -c "import …"`) → W (`>`/`>>` redirect unless the redirected sub-command is a program run)
→ E (every `&&|;|\|`-separated sub-command starts with ls/cat/head/tail/find/grep/which/pwd/tree/stat/wc/…, `git status|
log|show|…`, `pip list|show`, `--help|--version`, read-only `sed -n …p`, `sqlite3 … SELECT`; `echo` is neutral; `[read]`,
`[str_replace_editor …] view`) → X. terminus2 keystroke-only steps (Enter/C-c, screen changed) → X. R and O are not
emitted and excluded from accuracy (shown as rows for completeness).

**Step-level accuracy over the 52,978 steps whose human code ∈ {E,V,W,X,C,P}: 61.9 %** (FAIL 61.1, PASS 64.4).
**Segment-level (majority auto code of a human run = human code): 71.3 %** over 23,251 runs; human code appears somewhere in the run: 77.7 %.

Confusion matrix (rows = human, cols = auto):

| human \ auto | E | V | W | X | C | P |
|---|---|---|---|---|---|---|
| E (14,778) | **8899** | 1410 | 690 | 3662 | 2 | 115 |
| V (9,265) | 3227 | **2679** | 553 | 2690 | 62 | 54 |
| W (11,378) | 648 | 451 | **7934** | 2273 | 57 | 15 |
| X (14,933) | 919 | 1650 | 926 | **11328** | 36 | 74 |
| C (1,632) | 60 | 43 | 29 | 176 | **1304** | 20 |
| P (992) | 65 | 36 | 115 | 138 | 4 | **634** |
| R (7,441, not scored) | 2093 | 687 | 1392 | 3172 | 60 | 37 |
| O (2,857, not scored) | 89 | 112 | 77 | 2484 | 18 | 77 |

| code | recall % | precision % | F1 | segment-majority % | | scaffold | step acc % | segment-majority % | | model | step acc % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E | 60.2 | 64.4 | 0.62 | 69.3 | | miniswe | 65.7 | 72.5 | | claude | 66.0 |
| V | **28.9** | 42.7 | **0.35** | 31.5 | | openhands | 64.4 | 75.4 | | deepseek-v3.2 | 56.7 |
| W | 69.7 | 77.4 | 0.73 | 89.0 | | terminus2 | **56.6** | **64.3** | | devstral | 54.8 |
| X | 75.9 | 55.9 | 0.64 | 77.7 | | | | | | gemini | 70.5 |
| C | 79.9 | 89.0 | 0.84 | 87.3 | | | | | | gpt5 | 53.5 |
| P | 63.9 | 69.5 | 0.67 | 76.7 | | | | | | kimi | 65.3 |
| | | | | | | | | | | qwen | 67.3 |

Reading: C, W and P are recoverable from syntax (F1 0.67–0.84); E/X are moderately recoverable; **V is not** — annotators
code "verify" by intent (`cat result.txt`, `ls -la /srv/shared`, `python solve.py` after a fix, `pmars` benchmark runs
→ human V) and the classifier sees E/X (3,227 + 2,690 of 9,265 V steps). Two-thirds of V→E are `cat`/`ls`/`head`/`wc`.
Human R (7,441 steps) is spread over all auto codes, confirming R is a trajectory-relative label. Human segment
granularity also caps step-level agreement (a run coded W may contain a `cat` check): the segment-majority view is the
fairer number (71.3 %). terminus2 is the worst scaffold on every detector; its tmux-screen format (echoed commands,
no exit codes, keystroke-only steps) is the common cause.

## Anomalies worth acting on

1. **Evidence fields are not verbatim** (E1.2): 95.8 % miss under the codebook's own definition; 46.6 % share <30 % of
   content tokens with the cited step. `t_commit_evidence` (recall 0.22) and `suspicious_pass_evidence` are narrative.
   Either re-define the field as "grounded description" in the codebook or re-extract verbatim quotes in E3.
2. **t_surface semantics** (E1.1): the human label is a failure-*relevant* signal; the regex finds an earlier, unrelated
   error in 81.5 % of cases, and 28.3 % "surface before lock-in" becomes 78.5 % under the regex. The paper text for
   Finding 3 / M14 must say which definition is used; the silent share (23.6 vs 28.0 %) is the only number that transfers.
3. **216 human-silent trajectories carry a regex error signal** — candidate missed labels for E3 review (most look like
   transient early errors; devstral has the largest gap, 18.2 % auto vs 30.3 % human silent).
4. **Fabrication regex baseline is uninformative** (E1.3): flat 26–30 % human rate across labels; terminus2 precision 8 %.
   The LLM claim-extraction pass is a prerequisite, not an add-on.
5. **V is the weakest action code** (E1.4 recall 29 %); E/V and X/V boundaries are intent-based. terminus2 agreement is
   8–9 pts below the other scaffolds on E1.4 and the worst on E1.3 because of its export format.
6. Data-format issues to document in the paper's data statement: terminus2 devstral/gemini commands live only inside the
   raw model JSON; 266 openhands steps have `execute_bash(<missing command>)`; openhands `TOOL think` content is in
   `terminal_result`, not `agent_analysis`.

Outputs: `tsurface_auto.json`, `evidence_hits.json`, `evidence_miss.csv`, `fabrication_auto.json`, `segments_auto.json`
(each JSON has `summary` + per-row records). Logs in `resub/logs/e1_*.log`.
