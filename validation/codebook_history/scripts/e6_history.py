"""E6 deliverable 3: draft CODEBOOK_HISTORY.md (5-part structure) with real case ids drawn from the data.
Only states what the retained files show; intermediate artifacts are marked 'not retained'."""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from e6_common import OUT, pairs, load_index, load_v2, load_data_files, pct, md_table, V1_CATEGORY_FIELD, is_fail_v2

idx = load_index()
v2 = load_v2()
d355, d826 = load_data_files()
P_all = pairs()
P = [p for p in P_all if p["v2_fail"]]
odd = [p for p in P_all if not p["v2_fail"]]
fails = [r for r in v2.values() if is_fail_v2(r)]
passes = [r for r in v2.values() if not is_fail_v2(r)]
mapping = json.load(open(os.path.join(OUT, "v1_to_v2_mapping.json")))
schema = json.load(open(os.path.join(OUT, "v1_schema.json")))

def q(s, n=160):
    s = (s or "").replace("\n", " ").replace("|", "/")
    return s if len(s) <= n else s[:n - 3] + "..."

def case_line(p, extra=""):
    v1, r = p["v1"], p["v2"]
    return (f"- **`{p['case_id']}`** ({p['agent']}/{p['model']}, m={r['m']}; v1 m={p['v1_m']}). "
            f"v1: `{v1['primary_failure_category']}` / `{v1['primary_failure_subtype']}`, n={p['n']}; "
            f"v2: t_err={r['t_err']}, t_commit={r['t_commit']}, t_surface={r['t_surface']}, trigger=`{r['trigger_mechanism']}`, "
            f"awareness=`{r['awareness']}`, recovery_attempts={r['num_recovery_attempts']}. "
            f"v1 summary: \"{q(v1['one_sentence_failure_summary'])}\" v2 t_err evidence: \"{q(r['t_err_evidence'], 100)}\"; t_commit evidence: \"{q(r['t_commit_evidence'], 100)}\". {extra}")

m_eq = [p for p in P if p["v1_m"] == p["v2_m"]]

# A. multiple errors: v1 marked the onset (n == t_err) but v2 places lock-in >5 steps later, after further attempts
A = sorted([p for p in m_eq if p["n"] == p["v2"]["t_err"] and p["v2"]["t_commit"] - p["n"] > 5 and p["v2"]["num_recovery_attempts"] > 0],
           key=lambda p: -(p["v2"]["t_commit"] - p["n"]))[:2]
A_n = sum(1 for p in m_eq if p["v2"]["t_commit"] - p["v2"]["t_err"] > 5)
# A2: v1 n sits strictly between t_err and t_commit (single marker could not express the span)
A2 = sorted([p for p in m_eq if p["v2"]["t_err"] < p["n"] < p["v2"]["t_commit"] and p["v2"]["t_commit"] - p["v2"]["t_err"] > 10],
            key=lambda p: -(p["v2"]["t_commit"] - p["v2"]["t_err"]))[:2]
A2_n = sum(1 for p in m_eq if p["v2"]["t_err"] < p["n"] < p["v2"]["t_commit"])

# B. recovered errors: (i) FAIL pairs where v1 n precedes v2 t_err by >5 (v1 pointed at an earlier error that v2 judged non-decisive)
B1 = sorted([p for p in m_eq if p["v2"]["t_err"] - p["n"] > 5 and p["n"] >= 1], key=lambda p: -(p["v2"]["t_err"] - p["n"]))[:2]
B1_n = sum(1 for p in m_eq if p["v2"]["t_err"] - p["n"] > 5 and p["n"] >= 1)
# (ii) PASS with errors recovered (v1 had no way to record)
B2 = sorted([r for r in passes if r["num_error_events"] > 0 and r["num_recoveries"] > 0], key=lambda r: (-r["num_recoveries"], -r["max_detour_length"]))[:2]
pass_err = sum(1 for r in passes if r["num_error_events"] > 0)
pass_rec = sum(1 for r in passes if r["num_recoveries"] > 0)

# C. category boundary: most dispersed v1 category (for prose) + largest category's dominant subtype (for examples, m-equal only)
per_cat = mapping["per_v1_category"]
worst_cat = max(per_cat, key=lambda c: (per_cat[c]["v2_trigger_normalized_entropy"] if per_cat[c]["n"] >= 30 else -1))
big_cat = max(per_cat, key=lambda c: per_cat[c]["n"])
sub_groups = collections.defaultdict(list)
for p in m_eq:
    if p["v1"][V1_CATEGORY_FIELD] == big_cat:
        sub_groups[p["v1"]["primary_failure_subtype"]].append(p)
C_subtype, C_ps = max(sub_groups.items(), key=lambda kv: len(kv[1]))
C_trig = collections.Counter(p["v2"]["trigger_mechanism"] for p in C_ps)
C = []
for t, _ in C_trig.most_common(2):
    C.append(next(p for p in C_ps if p["v2"]["trigger_mechanism"] == t))
# C2: v2 coined categories outside the v1 vocabulary
V1_CAT_VOCAB = set(per_cat)
C2 = [p for p in P if p["v2"][V1_CATEGORY_FIELD] not in V1_CAT_VOCAB][:2]
C2_n = sum(1 for p in P if p["v2"][V1_CATEGORY_FIELD] not in V1_CAT_VOCAB)

# D. coverage: FAIL without v1; PASS never annotated; silent failures; fabrication side-audit; invalid n
no_v1_fail = [it for it in idx if not it["v1_annotation"] and is_fail_v2(v2[it["case_id"]])]
no_v1_by = collections.Counter((it["agent"], it["model"]) for it in no_v1_fail)
silent = [p for p in m_eq if p["v2"]["t_surface"] is None]
D_silent = sorted(silent, key=lambda p: -p["v2"]["m"])[:2]
fab_flag = [it for it in idx if it["fabrication_info"]]
fab_with_v1 = sum(1 for it in fab_flag if it["v1_annotation"])
n0 = [p for p in P if p["n"] < 1]

# v2 stats for part 4
def cnt(recs, f):
    return collections.Counter(str(r.get(f)) for r in recs)
unc = collections.Counter(f for r in fails for f in r.get("uncertain_fields", []))
m_ne = [p for p in P if p["v1_m"] != p["v2_m"]]
m_ne_tasks = collections.Counter(p["task_id"] for p in m_ne)
o = mapping["offset_t_commit_minus_n"]["all"]
oeq = mapping["offset_t_commit_minus_n"]["m_equal"]

L = []
L.append("# Codebook history: from the coarse first pass to the v2 three-timepoint scheme\n")
L.append("> DRAFT for the resubmission (Section II-F). Generated by `resub/scripts/e6_history.py`; every number below is recomputed from the retained files "
         "(`Data/completed_traj_data*.json`, `v2_tasks/annotation_index*.json`, `traj_data_v2_all89tasks.json`, `CODEBOOK.md`). "
         "Statements attributed to the authors' account (rounds, head-counts, discussion process) come from `rebuttal_review_notes.md` and are marked as such; "
         "where the corresponding artifact is not in the repository the text says **not retained**. Supporting tables: `resub/e6/v1_schema.md`, `resub/e6/v1_to_v2_mapping.md`.\n")

# ---- Part 1
L.append("## 1. Coarse first pass (authors' account; artifacts not retained)\n")
L.append("According to the authors (rebuttal notes, 2026-09-26), four annotators (all co-authors; three CS undergraduates) each read a **different** set of 200 trajectories "
         "(800 in total) and, from that reading, agreed on three broad root-cause groups and an initial codebook consensus. "
         "**Not retained:** the per-annotator 200-trajectory assignments, the notes or codes produced in this pass, and the wording of the three groups. "
         "No file in the repository is dated to or labelled as this pass, so no count of codes from it is reported here.\n")
L.append(f"What the retained files do show is the *result* of that consensus, i.e. the v1 scheme (next section). Its top-level `primary_failure_layer` field has three dominant values "
         f"(`model` {schema['v1_vocab']['primary_failure_layer'].get('model')}, `agent` {schema['v1_vocab']['primary_failure_layer'].get('agent')}, "
         f"`environment` {schema['v1_vocab']['primary_failure_layer'].get('environment')}; `task` {schema['v1_vocab']['primary_failure_layer'].get('task')}) over the {schema['sources']['index_with_v1']} retained v1 objects. "
         "This is consistent with a three-group origin but is not by itself proof that these were the three groups of the coarse pass.\n")

# ---- Part 2
L.append("## 2. v1 applied to the full corpus, and the problems it exposed\n")
L.append("### 2.1 What v1 was\n")
L.append(f"v1 is a **single-marker, FAIL-only** scheme: one root-cause triple (`primary_failure_layer` / `primary_failure_category` / `primary_failure_subtype`), "
         f"an optional contributing triple, a free-text `root_cause_label`, a reasoning paragraph, and exactly one step index `n` (stored as `command_index_ratio.n`, with `m` = length). "
         f"Only `layer` ({len(schema['v1_vocab']['primary_failure_layer'])} values) and `category` ({len(schema['v1_vocab']['primary_failure_category'])} values) were vocabulary-controlled; "
         f"`subtype` was free text and realised {schema['v1_subtype_distinct']} distinct strings over {schema['sources']['index_with_v1']} records. Full field list and frequencies: `v1_schema.md`.\n")
L.append("### 2.2 Retained v1 artifacts\n")
L.append(md_table(["file", "records", "models", "note"], [
    ("`Data/completed_traj_data.json`", schema["data_files"][0]["records"], ", ".join(schema["data_files"][0]["models"]), f"all `fail`; {schema['data_files'][0]['in_index_v1']} reappear verbatim (modulo `Devstral-2`->`Devstral`) in the v2 index"),
    ("`Data/completed_traj_data_merged_with_repaired.json`", schema["data_files"][1]["records"], ", ".join(schema["data_files"][1]["models"]), f"all `fail`; {schema['data_files'][1]['in_index_v1']} reappear in the v2 index (one typo fixed)"),
    ("`v2_tasks/annotation_index*.json` -> `v1_annotation`", schema["sources"]["index_with_v1"], "all 7", "the v1 objects handed to the v2 annotator as context"),
]))
L.append(f"\nThe two `Data/` files together cover all {schema['sources']['index_with_v1']} v1 objects in the index plus {len(schema['data_files'][0]['not_in_index'])+len(schema['data_files'][1]['not_in_index'])} records for cases later dropped from the corpus "
         "(e.g. `solve-maze-challenge`, `speech-to-text`, `train-fasttext`, and duplicate model spellings). "
         "The filename suffix `merged_with_repaired` indicates a repair/merge step; what was repaired is **not retained**. "
         "Per-annotator ownership of v1 records is **not retained** (no annotator field exists in v1 objects).\n")
L.append("### 2.3 Problems exposed by the full v1 application\n")
L.append("The authors list four problem types: multiple errors, recovered errors, category boundaries, and insufficient coverage. The retained v1/v2 pairs let us show each one on real cases "
         f"(v1 `n` vs v2 `t_err`/`t_commit`; {len(m_eq)} FAIL pairs with identical step count `m` in both rounds are used for step comparisons).\n")

L.append("#### (a) Multiple errors: one marker cannot hold both the onset and the lock-in\n")
L.append(f"In v2, t_commit - t_err > 5 steps in {A_n}/{len(m_eq)} ({pct(A_n, len(m_eq)):.1f}%) m-equal FAIL pairs. In v1 the annotator had to pick one step. "
         f"Below, v1 `n` equals the v2 onset `t_err` while v2 places the lock-in much later, after further failed attempts (selected: largest t_commit - n among such cases):\n")
for p in A:
    L.append(case_line(p))
L.append(f"\nConversely, in {A2_n} m-equal pairs v1 `n` lies strictly between the v2 onset and lock-in, i.e. v1 pointed somewhere inside the error span (two with the widest span):\n")
for p in A2:
    L.append(case_line(p))

L.append("\n#### (b) Recovered errors: an early error that the agent later fixed is not the decisive one\n")
L.append(f"(i) In {B1_n} m-equal FAIL pairs the v1 marker precedes the v2 `t_err` by more than 5 steps: the v1 marker sits on an earlier error that the v2 annotator did not judge decisive (largest gap first):\n")
for p in B1:
    L.append(case_line(p))
L.append(f"\n(ii) v1 had no PASS schema, so error-then-recovery in successful runs was unrepresentable. In v2, {pass_err}/{len(passes)} ({pct(pass_err, len(passes)):.1f}%) PASS trajectories record at least one error event and {pass_rec} record at least one recovery. Two examples (most recoveries):\n")
for r in B2:
    L.append(f"- **`{r['case_id']}`** (m={r['m']}): num_error_events={r['num_error_events']}, num_recoveries={r['num_recoveries']}, max_detour_length={r['max_detour_length']}, "
             f"solution_directness=`{r['solution_directness']}`. first error: \"{q(r['first_error_evidence'], 100)}\". strategy: \"{q(r['one_sentence_strategy_summary'], 140)}\"")

L.append("\n#### (c) Category boundaries: one v1 category, several mechanisms\n")
pc = per_cat[worst_cat]
L.append(f"The v1 category with the most dispersed v2 mapping (among categories with >= 30 cases) is `{worst_cat}` (N={pc['n']}): modal v2 trigger `{pc['v2_trigger_modal']}` covers only {pc['v2_trigger_modal_share']}%, "
         f"{pc['n_distinct_v2_triggers']} different triggers appear, normalised entropy {pc['v2_trigger_normalized_entropy']}. The largest v1 category, `{big_cat}` (N={per_cat[big_cat]['n']}), maps to `{per_cat[big_cat]['v2_trigger_modal']}` in only {per_cat[big_cat]['v2_trigger_modal_share']}% and spreads over all {per_cat[big_cat]['n_distinct_v2_triggers']} triggers. Full matrix: `v1_to_v2_mapping.md` section 1. "
         f"Even at the subtype level the boundary is not sharp: the most frequent v1 subtype under `{big_cat}`, `{C_subtype}` ({len(C_ps)} m-equal pairs), splits into " + ", ".join(f"`{t}` {n}" for t, n in C_trig.most_common()) + ". Two cases with the same v1 category+subtype but different v2 trigger:\n")
for p in C:
    L.append(case_line(p))
L.append(f"\nThe boundary problem persisted into the retained v1 taxonomy fields of v2: because the v2 prompt typed `primary_failure_layer/category` as free strings, the v2 annotator coined values outside the 11-value v1 vocabulary in {C2_n}/{len(P)} pairs "
         f"({schema['v2_vocab_drift']['primary_failure_category_distinct']} distinct categories overall). Two examples:\n")
for p in C2:
    L.append(f"- **`{p['case_id']}`**: v1 `{p['v1']['primary_failure_category']}` -> v2 `{p['v2']['primary_failure_category']}` (v2 trigger `{p['v2']['trigger_mechanism']}`).")
L.append("\nThe controlled root-cause field in v2 is therefore `trigger_mechanism`; the retained fields are carried for continuity only.\n")

L.append("#### (d) Insufficient coverage\n")
L.append(f"- **PASS trajectories**: v1 annotated FAIL only (all {schema['sources']['index_with_v1']} retained v1 objects have `outcome = fail`); the {len(passes)} PASS trajectories had no annotation at all before v2.")
L.append(f"- **FAIL trajectories without a v1 object**: {len(no_v1_fail)} of the {len(fails)} final FAIL trajectories carry no `v1_annotation` "
         "(by scaffold/model: " + ", ".join(f"{a}/{m} {n}" for (a, m), n in no_v1_by.most_common()) + "). Why they were missed in v1 is **not retained**. Examples: "
         + ", ".join(f"`{it['case_id']}`" for it in no_v1_fail[:2]) + ".")
L.append(f"- **Silent failures**: v1 had no field for whether a failure signal ever surfaced. In v2, `t_surface` is null in {sum(1 for r in fails if r['t_surface'] is None)}/{len(fails)} FAIL records. "
         "Two long silent cases that v1 could only summarise in prose: " + "; ".join(f"`{p['case_id']}` (m={p['v2']['m']}, v1 n={p['n']}, v2 t_err={p['v2']['t_err']}, t_commit={p['v2']['t_commit']})" for p in D_silent) + ".")
L.append(f"- **Fabrication**: not a v1 field. A separate audit pre-flagged {len(fab_flag)} cases (`fabrication_info` in the index; {fab_with_v1} of them have a v1 object); v2 made `fabrication_present/type/onset_step/evidence` part of the schema.")
L.append(f"- **Invalid marker values**: {len(n0)} v1 objects have n = 0 (outside the 1-indexed range): " + ", ".join(f"`{p['case_id']}` (v2 t_commit={p['v2']['t_commit']})" for p in n0) + ".")
L.append(f"- **Outcome inconsistency**: {len(odd)} case(s) are `fail` in v1 but PASS in the final index/v2: " + ", ".join(f"`{p['case_id']}`" for p in odd) + ". The reason (re-run or re-scored outcome) is **not retained**.")
L.append(f"- **Step count drift**: v1 `m` differs from v2 `m` in {len(m_ne)} pairs (v1 shorter in {sum(1 for p in m_ne if p['v1_m'] < p['v2_m'])}), concentrated in " +
         ", ".join(f"`{t}` {n}" for t, n in m_ne_tasks.most_common(6)) + ". The transcripts used in v1 for these cases are **not retained**, so their markers are not step-comparable.\n")

# ---- Part 3
L.append("## 3. Revision (what changed in the codebook)\n")
L.append("The revision is documented by the v2 prompt frozen in `CODEBOOK.md` section 6 and by the field diff in `v1_schema.md` section 4. Discussion minutes and intermediate drafts of the codebook are **not retained**. The changes that the files prove:\n")
L.append("1. **Time definition split in three.** The single `n` became `t_err` (decisive mistake), `t_commit` (lock-in; the prompt states 'Same as v1 field n'), and `t_surface` (first observable signal; null = silent), each with a verbatim evidence quote and a `timepoint_confidence`. Invariant `1 <= t_err <= t_commit <= m` enforced (`validate_v2.py`, C1-C4).")
L.append("2. **Controlled mechanism vocabulary (8+1).** `trigger_mechanism` with eight defined values plus `other` (requires `trigger_mechanism_other`), replacing the free-text subtype as the analysable root-cause field.")
L.append("3. **Process fields.** Forewarning (types + first step strictly before t_commit), awareness after t_commit, tail behaviour, fabrication, verification, and `action_segments` covering every step.")
L.append("4. **PASS schema.** A separate success-characterisation schema (error events, recoveries, detours, near-miss, suspicious pass, directness) so that recovered errors in successful runs are recorded.")
L.append("5. **Bookkeeping.** `schema_version`, `long_traj` (sampling rule for m > 120), `uncertain_fields`. Task-level metadata (`task_category/difficulty/type`) and `reasoning_en` dropped from the annotation object.\n")
L.append("Not changed: the v1 taxonomy triple and `root_cause_label` were kept in the FAIL schema as free strings (see 2.3(c) for the consequence).\n")

# ---- Part 4
L.append("## 4. v2 re-annotation of the whole corpus\n")
L.append(f"- All {len(v2)} trajectories in `traj_data_v2_all89tasks.json` carry `schema_version = v2`: {len(fails)} FAIL, {len(passes)} PASS. The v1 object, where it existed ({len(P_all)} cases), was supplied as context; the annotator re-judged independently (`CODEBOOK.md` section 1).")
L.append(f"- Realised vocabularies and the 16 invariants (0 violations) are in `CODEBOOK.md`; `uncertain_fields` was used on {sum(unc.values())} field-flags across FAIL records (top: " + ", ".join(f"`{k}` {n}" for k, n in unc.most_common(4)) + ").")
L.append(f"- **Agreement of the kept marker with v1.** On the {o['N']} FAIL pairs, t_commit = n exactly in {o['exact_pct']}%, within +/-1 in {o['within_1_pct']}%, within +/-3 in {o['within_3_pct']}%; |d| > 5 in {o['beyond_5_pct']}% "
         f"(m-equal subset, N={oeq['N']}: {oeq['exact_pct']}% / {oeq['within_1_pct']}% / {oeq['within_3_pct']}%). The v2 lock-in is later than n in {o['v2_later']} cases and earlier in {o['v2_earlier']}. Breakdown by scaffold and model: `v1_to_v2_mapping.md` section 3.")
L.append(f"- **Which v2 timepoint v1 `n` actually corresponds to.** The v2 prompt declares t_commit 'Same as v1 field n', but empirically n coincides with t_err ({o['t_err_minus_n_exact_pct']}% exact) more often than with t_commit ({o['exact_pct']}% exact); "
         f"n == t_err == t_commit in {o['n_position'].get('n==t_err==t_commit',0)} pairs, n == t_err only in {o['n_position'].get('n==t_err',0)}, n == t_commit only in {o['n_position'].get('n==t_commit',0)}, n before t_err in {o['n_position'].get('n<t_err',0)}, strictly between in {o['n_position'].get('t_err<n<t_commit',0)}, after t_commit in {o['n_position'].get('n>t_commit',0)}. "
         "In practice the v1 single marker behaved as an onset marker at least as often as a lock-in marker; the paper should describe `n` as 'the single v1 failure step' rather than as identical to t_commit.")
L.append(f"- **Category migration.** The retained `primary_failure_category` string changed in {mapping['overall_change_rate_retained_fields_pct']['primary_failure_category']}% of pairs; the three largest v1-category -> v2-trigger cells are " +
         "; ".join(f"`{c}` -> `{t}` ({n})" for c, t, n in mapping["largest_cells"][:3]) + ".")
L.append("- What is **not retained** from this round: per-annotator review assignments, the pre-discussion labels used for the kappa computation (the published kappa CSV is referenced in `rebuttal_review_notes.md`), and the list of records changed during human cross-checking of the LLM drafts.\n")

# ---- Part 5
L.append("## 5. Validation added for the resubmission (placeholder)\n")
L.append("_To be filled from E1 (detection-oracle / silent-failure audit), E3, and E4 (counterfactual repair feasibility) once those experiments are complete._\n")

open(os.path.join(OUT, "CODEBOOK_HISTORY.md"), "w").write("\n".join(L))
print("wrote CODEBOOK_HISTORY.md")
print("A", [p["case_id"] for p in A], "A2", [p["case_id"] for p in A2])
print("B1", [p["case_id"] for p in B1], "B2", [r["case_id"] for r in B2])
print("C", worst_cat, C_subtype, [p["case_id"] for p in C], "C2", [p["case_id"] for p in C2])
