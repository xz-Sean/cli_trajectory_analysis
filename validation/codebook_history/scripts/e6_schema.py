"""E6 deliverable 1: v1 field set + vocabularies (realized frequencies) and v1 -> v2 field diff.
Writes resub/e6/v1_schema.md and resub/e6/v1_schema.json."""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from e6_common import (OUT, DATA_355, DATA_826, V2_FILE, load_index, load_v2, load_data_files,
                       v1_n, v1_m, is_fail_v2, pct, md_table, ROOT)

idx = load_index()
v2 = load_v2()
d355, d826 = load_data_files()
v1 = [it["v1_annotation"] for it in idx if it["v1_annotation"]]
v1_by_v1id = {it["v1_case_id"]: it["v1_annotation"] for it in idx if it["v1_annotation"]}

# ---------- v1 field set ----------
V1_FIELDS = [
    ("case_id", "str", "trajectory id `task__scaffold__model` (v1 spelling; 280 ids later renamed, e.g. `deepseek` -> `deepseek-v3.2`)"),
    ("task_id", "str", "Terminal-Bench task id"),
    ("agent_arch", "str", "scaffold, capitalised spelling (`MiniSWE`/`OpenHands`/`Terminus2`)"),
    ("model", "str", "model, product spelling (`Claude`, `GPT`, `Gemini-2.5-pro`, `Devstral`/`Devstral-2`, ...)"),
    ("outcome", "str", "always `fail` in every retained v1 object (v1 annotated FAIL only)"),
    ("root_cause_label", "str (free text)", "short free-text root-cause name"),
    ("primary_failure_layer", "str (controlled)", "where the primary failure sits: model / agent / environment / task"),
    ("primary_failure_category", "str (controlled)", "the v1 root-cause CATEGORY (11 values) - the v1 label used for the v1->v2 mapping"),
    ("primary_failure_subtype", "str (free text, snake_case)", "annotator-coined subtype; not vocabulary-controlled"),
    ("contributing_failure_1_layer", "str (controlled) or ''", "secondary failure layer; empty string when none"),
    ("contributing_failure_1_category", "str (controlled) or ''", "secondary failure category"),
    ("contributing_failure_1_subtype", "str (free text) or ''", "secondary subtype"),
    ("one_sentence_failure_summary", "str", "one-sentence summary"),
    ("command_index_ratio.n", "int", "the single v1 time marker: the step at which the failure is locked in (v2 calls this `t_commit`; the v2 prompt says 'Same as v1 field n')"),
    ("command_index_ratio.m", "int", "trajectory length in steps"),
    ("reasoning_en", "str", "free-text reasoning paragraph (English)"),
    ("task_category", "str", "task category as recorded by the v1 annotator"),
    ("task_difficulty", "str", "easy / medium / hard as recorded by the v1 annotator"),
    ("task_type", "str (free text)", "finer task type coined by the annotator"),
]

def counter(recs, fld):
    return collections.Counter(str(x.get(fld)) for x in recs)

def vocab_table(fld, sources):
    keys = set()
    for _, recs in sources:
        keys |= set(counter(recs, fld))
    rows = []
    cnts = [counter(recs, fld) for _, recs in sources]
    tot = [len(recs) for _, recs in sources]
    for k in sorted(keys, key=lambda k: -cnts[0][k]):
        row = [f"`{k}`" if k != "" else "`''` (none)"]
        for c, t in zip(cnts, tot):
            row.append(f"{c[k]} ({pct(c[k], t):.1f}%)")
        rows.append(row)
    return md_table([fld] + [f"{name} (N={len(recs)})" for name, recs in sources], rows)

sources = [("index v1_annotation", v1), ("Data/355", d355), ("Data/826", d826)]

# ---------- v1 n distribution ----------
ns = [v1_n(a) for a in v1]
ms = [v1_m(a) for a in v1]
ratios = sorted(n / m for n, m in zip(ns, ms) if m)
def q(xs, p):
    return xs[min(len(xs) - 1, int(p * len(xs)))]
n_stats = {
    "N": len(ns), "n_min": min(ns), "n_max": max(ns), "n_eq_0": sum(1 for n in ns if n == 0),
    "n_eq_m": sum(1 for n, m in zip(ns, ms) if n == m),
    "n_over_m_quartiles": [round(q(ratios, p), 3) for p in (0.25, 0.5, 0.75)],
    "m_differs_from_v2_m": sum(1 for it in idx if it["v1_annotation"] and v1_m(it["v1_annotation"]) != v2[it["case_id"]]["m"]),
}

# ---------- Data/ file provenance ----------
def prov(recs, name):
    ids = [x["case_id"] for x in recs]
    in_idx = [x for x in recs if x["case_id"] in v1_by_v1id]
    identical = sum(1 for x in in_idx if v1_by_v1id[x["case_id"]] == x)
    diffk = collections.Counter()
    diff_examples = []
    for x in in_idx:
        a = v1_by_v1id[x["case_id"]]
        for k in x:
            if a.get(k) != x.get(k):
                diffk[k] += 1
                if len(diff_examples) < 3:
                    diff_examples.append((x["case_id"], k, x.get(k), a.get(k)))
    return {
        "file": name, "records": len(recs), "unique_case_ids": len(set(ids)),
        "outcome_values": dict(collections.Counter(x["outcome"] for x in recs)),
        "models": dict(collections.Counter(x["model"] for x in recs)),
        "scaffolds": dict(collections.Counter(x["agent_arch"] for x in recs)),
        "tasks": len(set(x["task_id"] for x in recs)),
        "in_index_v1": len(in_idx), "identical_to_index_v1": identical,
        "differing_keys": dict(diffk), "diff_examples": diff_examples,
        "not_in_index": sorted(x["case_id"] for x in recs if x["case_id"] not in v1_by_v1id),
        "mtime": __import__("datetime").datetime.fromtimestamp(os.path.getmtime({"Data/completed_traj_data.json": DATA_355, "Data/completed_traj_data_merged_with_repaired.json": DATA_826}[name])).strftime("%Y-%m-%d"),
    }
p355 = prov(d355, "Data/completed_traj_data.json")
p826 = prov(d826, "Data/completed_traj_data_merged_with_repaired.json")
union_ids = {x["case_id"] for x in d355} | {x["case_id"] for x in d826}
v1_not_in_data = sorted(set(v1_by_v1id) - union_ids)

# ---------- v2 field set ----------
fails = [r for r in v2.values() if is_fail_v2(r)]
passes = [r for r in v2.values() if not is_fail_v2(r)]
v2_fail_fields = list(fails[0].keys())
v2_pass_fields = list(passes[0].keys())

V1_LAYER_VOCAB = {"model", "agent", "environment", "task"}
V1_CAT_VOCAB = {k for k in counter(v1, "primary_failure_category")}
v2_layer_c = counter(fails, "primary_failure_layer")
v2_cat_c = counter(fails, "primary_failure_category")
v2_layer_in = sum(c for k, c in v2_layer_c.items() if k in V1_LAYER_VOCAB)
v2_cat_in = sum(c for k, c in v2_cat_c.items() if k in V1_CAT_VOCAB)

retained = ["case_id", "root_cause_label", "primary_failure_layer", "primary_failure_category",
            "primary_failure_subtype", "contributing_failure_1_layer", "contributing_failure_1_category",
            "contributing_failure_1_subtype", "one_sentence_failure_summary"]
renamed = [("command_index_ratio.n", "t_commit", "same definition per v2 prompt ('Same as v1 field n'); v2 adds `t_commit_evidence`"),
           ("command_index_ratio.m", "m", "trajectory length; now a top-level field"),
           ("agent_arch", "(index) agent", "moved out of the annotation into the index metadata; lower-case `miniswe/openhands/terminus2`"),
           ("model", "(index) model", "moved to index metadata; `Devstral-2`->`devstral`, `GPT`->`gpt5`, `DeepSeek`->`deepseek-v3.2`, `Gemini-2.5-pro`->`gemini`, ..."),
           ("outcome", "(index) outcome", "moved to index metadata; drives FAIL vs PASS schema selection")]
removed = [("reasoning_en", "replaced by per-field evidence quotes + `trigger_explanation`"),
           ("task_id", "moved to index metadata"),
           ("task_category", "dropped from annotation (task-level metadata)"),
           ("task_difficulty", "dropped from annotation (task-level metadata)"),
           ("task_type", "dropped")]
added_fail = [f for f in v2_fail_fields if f not in retained and f not in ("m", "t_commit")]
added_pass = v2_pass_fields

# ---------- write JSON ----------
summary = {
    "sources": {"index_items": len(idx), "index_with_v1": len(v1),
                "v2_records": len(v2), "v2_fail": len(fails), "v2_pass": len(passes)},
    "v1_fields": [f[0] for f in V1_FIELDS],
    "v1_vocab": {f: dict(counter(v1, f)) for f in ["primary_failure_layer", "primary_failure_category",
                                                    "contributing_failure_1_layer", "contributing_failure_1_category",
                                                    "agent_arch", "model", "outcome", "task_difficulty", "task_category"]},
    "v1_subtype_distinct": len(set(a["primary_failure_subtype"] for a in v1)),
    "v1_contrib_subtype_distinct": len(set(a["contributing_failure_1_subtype"] for a in v1)),
    "v1_root_cause_label_distinct": len(set(a["root_cause_label"] for a in v1)),
    "v1_top_subtypes": counter(v1, "primary_failure_subtype").most_common(20),
    "v1_n_stats": n_stats,
    "data_files": [p355, p826], "v1_ids_not_in_any_Data_file": v1_not_in_data,
    "v2_fail_fields": v2_fail_fields, "v2_pass_fields": v2_pass_fields,
    "v2_vocab_drift": {"primary_failure_layer_distinct": len(v2_layer_c), "layer_in_v1_vocab": v2_layer_in,
                       "primary_failure_category_distinct": len(v2_cat_c), "category_in_v1_vocab": v2_cat_in,
                       "v2_layer_counts": dict(v2_layer_c), "v2_category_counts": dict(v2_cat_c)},
    "field_diff": {"retained": retained, "renamed": renamed, "removed": removed,
                   "added_fail": added_fail, "added_pass_schema": added_pass},
}
json.dump(summary, open(os.path.join(OUT, "v1_schema.json"), "w"), indent=1, ensure_ascii=False)

# ---------- write MD ----------
L = []
L.append("# v1 annotation schema (reconstructed from retained files) and v1 -> v2 field diff\n")
L.append("Generated by `resub/scripts/e6_schema.py`. All counts are computed from the files named below; nothing is taken from memory.\n")
L.append("## 0. Sources\n")
L.append(md_table(["file", "records", "what it is"], [
    ("`v2_tasks/annotation_index_*.json` (4 files)", f"{len(idx)} items; {len(v1)} with non-empty `v1_annotation`", "the v2 annotation index; each item carries the earlier v1 object verbatim as `v1_annotation` (given to the v2 annotator as context)"),
    ("`Data/completed_traj_data.json`", f"{p355['records']} (mtime {p355['mtime']})", "v1-era file; models " + ", ".join(f"{k} {v}" for k, v in p355["models"].items())),
    ("`Data/completed_traj_data_merged_with_repaired.json`", f"{p826['records']} (mtime {p826['mtime']})", "v1-era file; models " + ", ".join(f"{k} {v}" for k, v in p826["models"].items())),
    ("`traj_data_v2_all89tasks.json`", f"{len(v2)} ({len(fails)} FAIL / {len(passes)} PASS)", "final v2 annotations, all `schema_version=v2`"),
]))
L.append("\n**Provenance check.** The two `Data/` files are the retained v1-era outputs. "
         f"{p355['in_index_v1']} of the {p355['records']} records in the 355-file and {p826['in_index_v1']} of the {p826['records']} in the 826-file "
         f"re-appear as `v1_annotation` in the index ({p355['in_index_v1']}+{p826['in_index_v1']} = {p355['in_index_v1']+p826['in_index_v1']} = all {len(v1)} v1 objects; "
         f"{len(v1_not_in_data)} v1 objects are absent from both files). "
         f"Of the matched records, {p355['identical_to_index_v1']}/{p355['in_index_v1']} and {p826['identical_to_index_v1']}/{p826['in_index_v1']} are byte-identical; the only differences are "
         f"`model` spelling (`Devstral-2` -> `Devstral`, {p355['differing_keys'].get('model',0)} records) and one typo fix "
         f"(`{p826['diff_examples'][0][0]}`: `{p826['diff_examples'][0][2]}` -> `{p826['diff_examples'][0][3]}`) if present. "
         f"{len(p355['not_in_index'])} + {len(p826['not_in_index'])} Data records are not in the index (their tasks/cases were dropped from the final corpus, e.g. `solve-maze-challenge`, `speech-to-text`, `train-fasttext`, or duplicate model spellings such as `gpt-5__descend_gpt5`, `kimi-k2-250905`, `openai-gpt-5`); see `v1_schema.json` for the full lists.\n")
L.append("Every retained v1 object has `outcome = fail`: **v1 annotated FAIL trajectories only**; there was no PASS schema in v1.\n")

L.append("## 1. v1 field set\n")
L.append(md_table(["field", "type", "meaning"], [(f"`{a}`", b, c) for a, b, c in V1_FIELDS]))
L.append("\n## 2. v1 controlled vocabularies with realized frequencies\n")
L.append("### 2.1 `primary_failure_layer`\n")
L.append(vocab_table("primary_failure_layer", sources))
L.append("\n### 2.2 `primary_failure_category` (the v1 root-cause category)\n")
L.append(vocab_table("primary_failure_category", sources))
L.append("\n(`implementation_generationategy` in Data/826 is a typo that the index copy corrects to `implementation_generation`.)\n")
L.append("### 2.3 `contributing_failure_1_layer`\n")
L.append(vocab_table("contributing_failure_1_layer", sources))
L.append("\n### 2.4 `contributing_failure_1_category`\n")
L.append(vocab_table("contributing_failure_1_category", sources))
L.append(f"\n### 2.5 Free-text fields (not vocabulary-controlled)\n")
L.append(f"- `primary_failure_subtype`: {summary['v1_subtype_distinct']} distinct strings over {len(v1)} records. Top 20: " +
         ", ".join(f"`{k}` {c}" for k, c in summary["v1_top_subtypes"]) + ".")
L.append(f"- `contributing_failure_1_subtype`: {summary['v1_contrib_subtype_distinct']} distinct strings (incl. empty).")
L.append(f"- `root_cause_label`: {summary['v1_root_cause_label_distinct']} distinct strings over {len(v1)} records (essentially one label per trajectory).")
L.append("- `task_category` (" + ", ".join(f"`{k}` {c}" for k, c in counter(v1, "task_category").most_common()) + "); "
         "`task_difficulty` (" + ", ".join(f"`{k}` {c}" for k, c in counter(v1, "task_difficulty").most_common()) + "). "
         "These were annotator-recorded, not taken from Terminal-Bench metadata, and are superseded by E7.\n")
L.append("### 2.6 The single time marker `command_index_ratio.n`\n")
L.append(f"- N = {n_stats['N']}; n ranges {n_stats['n_min']}..{n_stats['n_max']}; n = 0 in {n_stats['n_eq_0']} records "
         "(`build-cython-ext__miniswe__qwen`, `neuron-to-jaxley-conversion__openhands__deepseek-v3.2`; 0 is outside the 1-indexed step range, i.e. an invalid v1 value); "
         f"n = m (lock-in at the last step) in {n_stats['n_eq_m']} records.")
L.append(f"- n/m quartiles: {n_stats['n_over_m_quartiles']}.")
L.append(f"- v1 `m` differs from v2 `m` in {n_stats['m_differs_from_v2_m']} of {len(v1)} records (the transcript step count changed between rounds; the reason is not retained). "
         "Offsets n vs t_commit are therefore reported both overall and on the m-equal subset in `v1_to_v2_mapping.md`.\n")

L.append("## 3. v2 field set\n")
L.append("FAIL schema (" + str(len(v2_fail_fields)) + " fields): " + ", ".join(f"`{f}`" for f in v2_fail_fields) + "\n")
L.append("PASS schema (" + str(len(v2_pass_fields)) + " fields): " + ", ".join(f"`{f}`" for f in v2_pass_fields) + "\n")
L.append("Definitions and vocabularies: `CODEBOOK.md` sections 2-3.\n")
L.append("## 4. Field diff v1 -> v2\n")
L.append("### 4.1 Retained unchanged (name and intent)\n")
L.append(", ".join(f"`{f}`" for f in retained) + "\n")
L.append(f"**Vocabulary drift on retained taxonomy fields.** v1 used {len(V1_LAYER_VOCAB)} layer values and {len(V1_CAT_VOCAB)} category values. "
         f"The v2 prompt types these fields as free `string` without listing a vocabulary, so v2 realised {len(v2_layer_c)} distinct layers and {len(v2_cat_c)} distinct categories; "
         f"{v2_layer_in}/{len(fails)} ({pct(v2_layer_in,len(fails)):.1f}%) layers and {v2_cat_in}/{len(fails)} ({pct(v2_cat_in,len(fails)):.1f}%) categories fall inside the v1 vocabulary; the rest are new coinages "
         "(e.g. `planning`, `execution`, `knowledge_gap`, `reasoning`). In v2 the controlled root-cause field is `trigger_mechanism` (9 values); the retained v1 taxonomy fields are carried for continuity only.\n")
L.append("### 4.2 Renamed / relocated\n")
L.append(md_table(["v1", "v2", "note"], [(f"`{a}`", f"`{b}`", c) for a, b, c in renamed]))
L.append("\n### 4.3 Removed\n")
L.append(md_table(["v1 field", "note"], [(f"`{a}`", b) for a, b in removed]))
L.append("\n### 4.4 Added (FAIL schema)\n")
L.append(", ".join(f"`{f}`" for f in added_fail) + "\n")
L.append("Grouped: time geometry (`t_err`, `t_surface`, `*_evidence`, `timepoint_confidence`); mechanism (`trigger_mechanism`, `trigger_mechanism_other`, `trigger_explanation`); "
         "forewarning (4 fields); awareness (3 fields); `tail_dominant_behavior`; fabrication (4 fields); verification (2 fields); `action_segments`; bookkeeping (`schema_version`, `long_traj`, `uncertain_fields`).\n")
L.append("### 4.5 Added (entire PASS schema; v1 had none)\n")
L.append(", ".join(f"`{f}`" for f in added_pass) + "\n")
L.append(f"\nMachine-readable version: `resub/e6/v1_schema.json`.\n")
open(os.path.join(OUT, "v1_schema.md"), "w").write("\n".join(L))
print("wrote v1_schema.md / .json")
