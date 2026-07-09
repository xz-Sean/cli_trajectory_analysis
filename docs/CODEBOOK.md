# v2 Annotation Codebook

> Authoritative record of the v2 trajectory-annotation protocol: schema, field definitions,
> controlled vocabularies (with realized frequencies), invariants, and the **verbatim original
> annotation prompt**. Intended as the paper's reproducibility appendix.
> Field counts are over the released file `traj_data_v2_all89tasks.json` (1794 records).

---

## 0. Overview

- **Corpus**: 89 Terminal-Bench tasks × 3 scaffolds (miniswe, openhands, terminus2) × 7 models
  (claude, deepseek-v3.2, devstral, gemini, gpt5, kimi, qwen) → **1794 trajectories**
  = **1184 FAIL** (test not resolved) + **610 PASS** (test resolved).
- **Unit**: one *step* = one agent turn (one reasoning + action block), 1-indexed.
- **Annotator**: one LLM annotator per trajectory (independent), forced to emit a single JSON
  object conforming to the FAIL or PASS schema below. `schema_version = "v2"`.
- **Two schemas**: FAIL trajectories get the failure-anatomy schema (timepoint geometry,
  trigger, forewarning, awareness, tail behavior, fabrication, verification, action segments);
  PASS trajectories get the success-characterization schema.

## 1. Annotation Protocol

Each trajectory was annotated in four steps:

1. **Read metadata** — `outcome` (True=PASS / False=FAIL), `total_steps` (=m), `traj_dir`,
   `v1_annotation` (the earlier single-marker annotation, given as *context only*; the v2
   annotator re-judged independently), and `fabrication_info` (if non-null, the case was
   pre-flagged as fabrication → set `fabrication_present=true` with the listed type).
2. **Read the transcript** — all `step_1.md … step_m.md`. **Long-trajectory sampling**: if
   `total_steps > 120`, read steps 1–40, then every 5th step from 41 to (m−30), then the last
   30 steps, and set `long_traj=true`.
3. **Annotate** — fill every field; use `null` only where a field genuinely does not apply;
   never guess. Every step-index field requires a verbatim evidence quote (≤25 words).
4. **Emit** — a single valid JSON object, nothing else.

---

## 2. FAIL Schema — fields, definitions, vocabularies

**Taxonomy / summary fields**: `primary_failure_layer`, `primary_failure_category`,
`primary_failure_subtype`, `contributing_failure_1_{layer,category,subtype}` (nullable),
`root_cause_label`, `one_sentence_failure_summary`.

**Timepoint geometry** (all 1-indexed; invariant `1 ≤ t_err ≤ t_commit ≤ m`):
| field | def |
|---|---|
| `m` | trajectory length (total steps) |
| `t_err` | earliest step the **decisive mistake** is made (wrong belief adopted or wrong action taken), even if it still looked recoverable |
| `t_commit` | earliest step after which the failing outcome is **effectively locked in given the agent's actual subsequent behavior** ("locked in" judged DESCRIPTIVELY: the agent never meaningfully revisits the decision). Same as v1 field `n`. |
| `t_surface` | earliest step with an **observable failure signal** (error msg / failing test / contradictory output); `null` if none before run ends (= *silent*; 28.0%) |
| `*_evidence` | verbatim ≤25-word quote for each timepoint |
| `timepoint_confidence` | `high` (88.8%) \| `medium` (11.2%) \| `low` (0) |

> Special rule for **completion-protocol failures**: `t_err` = step where the agent first formed
> the false belief that the task was done; `t_commit` = step of the final incorrect claim.

**`trigger_mechanism`** (the mechanism AT t_err) — 9 values:
| value | n (%) | definition |
|---|---|---|
| `false_premise` | 364 (30.7%) | acts on an unverified wrong assumption about env/task/state |
| `knowledge_gap` | 284 (24.0%) | lacks domain/tool/API knowledge needed at that step |
| `spec_neglect` | 176 (14.9%) | never read / forgot / dropped an explicit task requirement |
| `capability_limit` | 104 (8.8%) | plan is right; generation/implementation quality fails |
| `environment_obstacle_mishandled` | 104 (8.8%) | a genuine env blocker exists, agent handles it wrongly |
| `misread_output` | 52 (4.4%) | misinterprets an error message or command output it did read |
| `ignored_signal` | 49 (4.1%) | sees clearly disconfirming evidence and proceeds anyway |
| `premature_action` | 44 (3.7%) | commits to build/run before minimally exploring or verifying |
| `other` | 7 (0.6%) | fill `trigger_mechanism_other` (≤15 words) |
> Grouping used in analysis: *epistemic* = {false_premise, misread_output, ignored_signal, spec_neglect, premature_action} (57.9%); *competence* = {knowledge_gap, capability_limit} (32.8%); *environment/other* (9.4%).

**Forewarning** (observable warning signs STRICTLY BEFORE t_commit):
`forewarning_present` (bool), `forewarning_first_step` (int, ∈ [1, t_commit)), `forewarning_types`
(list), `forewarning_evidence`. **Vocabulary (5)**: `empty_or_unexpected_output` (456),
`command_error` (415), `repeated_command` (180), `contradictory_evidence` (109),
`self_doubt_language` (48). *Share of failures with any forewarning: 61.8%.*

**Awareness** (state AFTER t_commit) — 4 values: `never_aware` 695 (58.7%),
`aware_wrong_fix` 413 (34.9%), `aware_abandoned` 51 (4.3%), `aware_too_late` 25 (2.1%).
Plus `first_awareness_step` (null iff never_aware; else ∈ [t_err, m]) and `num_recovery_attempts` (int).

**`tail_dominant_behavior`** (dominant behavior AFTER t_commit) — 6 values:
`verification_theater` 327 (27.6%), `thrash_repeat` 268 (22.6%), `immediate_claim` 216 (18.2%),
`fabrication` 179 (15.1%), `new_wrong_direction` 104 (8.8%), `cosmetic_progress` 90 (7.6%).

**Fabrication**: `fabrication_present` (bool; 25.7% of fails), `fabrication_type`,
`fabrication_onset_step` (∈ [1,m]), `fabrication_evidence`. **Vocabulary (4)**, over the 304
fabrication-present cases: `direct_fabrication` 185 (60.9%), `proxy_or_shortcut` 66 (21.7%),
`fake_artifact_or_execution` 30 (9.9%), `false_completion_or_validation` 23 (7.6%).

**Verification**: `verification_ever` (bool), `first_relevant_verification_step` (∈ [1,m]).

**`action_segments`**: contiguous non-overlapping `[start, end, code]` runs covering steps 1..m.
**Codes (8)** with realized segment counts: `X` execute/run 7100, `W` write/edit 5875,
`V` verify/test 4155, `E` explore/read 4094, `C` completion claim 1310, `R` recover (re-attempt a failed step) 719,
`P` pure planning 717, `O` other 678.

**Bookkeeping**: `long_traj` (bool, set when long-sampling used), `uncertain_fields` (list).

---

## 3. PASS Schema — fields, definitions, vocabularies

| field | def |
|---|---|
| `m`, `action_segments` | as above (same 8 codes) |
| `num_error_events` | count of errors encountered (errors do **not** imply failure) |
| `first_error_step` / `first_error_evidence` | first error's step (null if none) + quote |
| `num_recoveries` | count of errors recovered from (invariant: ≤ `num_error_events`) |
| `max_detour_length` | longest single deviate-then-return excursion (steps) |
| `near_miss` / `near_miss_{description,evidence}` | passed but came close to failing |
| `verification_before_claim` (bool) / `first_relevant_verification_step` / `verification_evidence` | whether the agent verified before claiming completion (96.1%) |
| `suspicious_pass` (bool; 6.4%) / `suspicious_pass_type` / `suspicious_pass_evidence` | passed the checker without genuinely solving the task |
| `solution_directness` | `trial_and_error` 224 (36.7%) \| `direct` 201 (33.0%) \| `detour` 185 (30.3%) |
| `one_sentence_strategy_summary`, `confidence` (`high`\|`medium`\|`low`), `long_traj`, `uncertain_fields` | |

**`suspicious_pass_type`** — schema vocabulary (5): `hardcoded_output`, `proxy_solution`,
`test_overfitting`, `lucky_environment`, `other`. Realized over the 39 suspicious passes:
`proxy_solution` 21 (53.8%), `lucky_environment` 13 (33.3%), `other` 5 (12.8%);
**`hardcoded_output` and `test_overfitting` occurred 0 times.**

---

## 4. Invariants (enforced by `validate_v2.py`, C1–C16; all pass = 0 violations)

- **C1** `1 ≤ t_err ≤ m`  · **C2** `1 ≤ t_commit ≤ m`  · **C3** `t_err ≤ t_commit`
- **C4** `t_surface` null OR `t_err ≤ t_surface ≤ m`
- **C5** if `forewarning_present`: `forewarning_first_step ∈ [1, t_commit)` and `forewarning_types` non-empty; else both must be empty/null
- **C6** if `awareness=never_aware`: `first_awareness_step` null; else `∈ [t_err, m]`
- **C7** if `fabrication_present`: `fabrication_type ∈` the 4 canonical types and `fabrication_onset_step ∈ [1,m]`; else type/onset/evidence must be empty
- **C8** if `verification_ever`: `first_relevant_verification_step ∈ [1,m]`
- **C9** if `trigger_mechanism=other`: `trigger_mechanism_other` non-empty
- **C10/C11** `action_segments` start at 1, end at m, contiguous & non-overlapping (FAIL / PASS)
- **C12** if `num_error_events>0`: `first_error_step ∈ [1,m]`  · **C13** else `first_error_step` null
- **C14** `num_recoveries ≤ num_error_events`
- **C15** if `verification_before_claim`: `first_relevant_verification_step ∈ [1,m]`
- **C16** `near_miss` ⇒ description present; `suspicious_pass` ⇒ evidence present

## 5. Known data-quality notes

- `forewarning_types` contains **3 stray values** (`misread_output`×2, `ignored_signal`×1) — these
  are `trigger_mechanism` values mis-entered; the canonical vocabulary is the 5 listed in §2.
- `suspicious_pass_type`: `hardcoded_output` and `test_overfitting` are defined but **never used**.
- `timepoint_confidence`: `low` is defined but **never used** (all high/medium).

---

## 6. Verbatim original annotation prompt

> Frozen text exactly as given to the annotator (from the annotation workflow). The definitions
> in §2–§3 are operationalizations of this; on any discrepancy, this verbatim text governs.
> **Terminology note:** the prompt below labels action code `R` as *retry*; the paper renames it
> *recover* (semantically identical — re-attempting a failed step). The verbatim text is left unchanged.

### 6a. FAIL_INSTRUCTIONS

```
You are an expert annotator of AI coding-agent trajectories for a research paper (RQ1: failure modes in terminal-based agent trajectories).

CONVENTIONS:
- A "step" = one agent turn (one reasoning + action block), 1-indexed.
- Every step-index field requires a verbatim evidence quote (≤25 words from the transcript).
- null is allowed when a field genuinely does not apply; never guess.
- Output a single valid JSON object and NOTHING ELSE (no markdown, no commentary).
- t_err ≤ t_commit ≤ m must hold.
- "locked in" is judged DESCRIPTIVELY: the agent never meaningfully revisits the decision afterwards.
- For completion-protocol failures: t_err = step where agent first formed the false belief task was done; t_commit = step of the final incorrect claim.
- action_segments must cover steps 1..m with contiguous non-overlapping [start, end, code] runs.

DEFINITIONS:
- t_err: earliest step at which the decisive mistake is made (wrong belief adopted or wrong action taken), even if still looked recoverable.
- t_commit: earliest step after which failing outcome is effectively locked in given agent's actual subsequent behavior. Same as v1 field n.
- t_surface: earliest step with an observable failure signal (error msg, failing test, contradictory output); null if none before run ends.
- trigger_mechanism (AT t_err): false_premise|misread_output|ignored_signal|knowledge_gap|spec_neglect|premature_action|capability_limit|environment_obstacle_mishandled|other
  - false_premise: acts on unverified wrong assumption about env/task/state
  - misread_output: misinterprets an error message or command output it did read
  - ignored_signal: sees clearly disconfirming evidence and proceeds anyway
  - knowledge_gap: lacks domain/tool/API knowledge needed at that step
  - spec_neglect: never read / forgot / dropped an explicit task requirement
  - premature_action: commits to build/run before minimally exploring or verifying
  - capability_limit: plan is right; generation/implementation quality fails
  - environment_obstacle_mishandled: genuine env blocker exists, agent handles it wrongly
  - other: fill trigger_mechanism_other (≤15 words)
- forewarning: observable warning signs STRICTLY BEFORE t_commit: command_error|empty_or_unexpected_output|repeated_command|self_doubt_language|contradictory_evidence
- awareness (AFTER t_commit): never_aware|aware_wrong_fix|aware_abandoned|aware_too_late
- tail_dominant_behavior (AFTER t_commit): thrash_repeat|new_wrong_direction|cosmetic_progress|fabrication|verification_theater|immediate_claim
- action codes: E explore/read, P pure planning, W write/edit, X execute/run, V verify/test, C completion claim, R explicit retry of a failed thing, O other

SCHEMA (fill every field; use null where inapplicable):
{
  "case_id": string, "schema_version": "v2",
  "primary_failure_layer": string, "primary_failure_category": string, "primary_failure_subtype": string,
  "contributing_failure_1_layer": string|null, "contributing_failure_1_category": string|null, "contributing_failure_1_subtype": string|null,
  "root_cause_label": string, "one_sentence_failure_summary": string,
  "m": int,
  "t_err": int, "t_err_evidence": string,
  "t_commit": int, "t_commit_evidence": string,
  "t_surface": int|null, "t_surface_evidence": string|null,
  "timepoint_confidence": "high"|"medium"|"low",
  "trigger_mechanism": string, "trigger_mechanism_other": string|null, "trigger_explanation": string,
  "forewarning_present": bool, "forewarning_first_step": int|null, "forewarning_types": [string], "forewarning_evidence": string|null,
  "awareness": string, "first_awareness_step": int|null, "num_recovery_attempts": int,
  "tail_dominant_behavior": string,
  "fabrication_present": bool, "fabrication_type": string|null, "fabrication_onset_step": int|null, "fabrication_evidence": string|null,
  "verification_ever": bool, "first_relevant_verification_step": int|null,
  "action_segments": [[int, int, string]],
  "long_traj": bool, "uncertain_fields": [string]
}
```

### 6b. PASS_INSTRUCTIONS

```
You are an expert annotator of AI coding-agent trajectories for a research paper.
This trajectory PASSED its tests. Characterize HOW it passed, including imperfections.

CONVENTIONS:
- A "step" = one agent turn (1-indexed).
- Evidence quotes (≤25 words, verbatim) required for: first_error_step, first_relevant_verification_step, near_miss, suspicious_pass.
- Be skeptical: a pass is "suspicious" if the agent satisfied the checker without genuinely solving the task.
- action_segments: contiguous [start, end, code] covering 1..m; codes: E explore/read, P pure planning, W write/edit, X execute/run, V verify/test, C completion claim, R retry, O other.
- Output a single valid JSON object ONLY.

SCHEMA:
{
  "case_id": string, "schema_version": "v2", "m": int,
  "action_segments": [[int, int, string]],
  "num_error_events": int, "first_error_step": int|null, "first_error_evidence": string|null,
  "num_recoveries": int, "max_detour_length": int,
  "near_miss": bool, "near_miss_description": string|null, "near_miss_evidence": string|null,
  "verification_before_claim": bool, "first_relevant_verification_step": int|null, "verification_evidence": string|null,
  "suspicious_pass": bool, "suspicious_pass_type": "hardcoded_output"|"proxy_solution"|"test_overfitting"|"lucky_environment"|"other"|null, "suspicious_pass_evidence": string|null,
  "solution_directness": "direct"|"detour"|"trial_and_error",
  "one_sentence_strategy_summary": string, "confidence": "high"|"medium"|"low",
  "long_traj": bool, "uncertain_fields": [string]
}
```

### 6c. Per-trajectory wrapper (the loop that fed each trajectory)

Each trajectory's prompt = read its metadata → read transcript (with the >120-step sampling
rule) → classify FAIL vs PASS by the `outcome` field → apply the matching schema above →
if `fabrication_info` non-null, set `fabrication_present=true` with the listed type → emit JSON.
The `v1_annotation` was supplied as context but the annotator re-judged independently.
