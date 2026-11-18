"""E6 deliverable 2: v1 category -> v2 trigger cross-tab, change rates, and (t_commit - n) offsets.
Writes resub/e6/v1_to_v2_mapping.json and .md."""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from e6_common import OUT, pairs, pct, md_table, V1_CATEGORY_FIELD, V1_LAYER_FIELD

P_all = pairs()
P = [p for p in P_all if p["v2_fail"]]          # FAIL in both rounds
odd = [p["case_id"] for p in P_all if not p["v2_fail"]]
TRIG = ["false_premise", "knowledge_gap", "spec_neglect", "capability_limit",
        "environment_obstacle_mishandled", "misread_output", "ignored_signal", "premature_action", "other"]
cats = [c for c, _ in collections.Counter(p["v1"][V1_CATEGORY_FIELD] for p in P).most_common()]

# ---------- cross-tab ----------
ct = {c: collections.Counter() for c in cats}
for p in P:
    ct[p["v1"][V1_CATEGORY_FIELD]][p["v2"]["trigger_mechanism"]] += 1
rowtot = {c: sum(ct[c].values()) for c in cats}
coltot = collections.Counter()
for c in cats:
    coltot.update(ct[c])

def entropy_norm(cnt):
    tot = sum(cnt.values())
    if tot == 0:
        return 0.0
    h = -sum((v / tot) * math.log(v / tot) for v in cnt.values() if v)
    return h / math.log(len(TRIG))

# ---------- change rates on retained fields ----------
def changed(p, f):
    return (p["v1"].get(f) or "") != (p["v2"].get(f) or "")
retained = ["primary_failure_layer", "primary_failure_category", "primary_failure_subtype",
            "contributing_failure_1_category", "root_cause_label"]
V1_CAT_VOCAB = set(cats)
per_cat = {}
for c in cats:
    sub = [p for p in P if p["v1"][V1_CATEGORY_FIELD] == c]
    modal, modal_n = ct[c].most_common(1)[0]
    per_cat[c] = {
        "n": len(sub),
        "v2_trigger_modal": modal, "v2_trigger_modal_share": round(pct(modal_n, len(sub)), 1),
        "v2_trigger_dispersion_1_minus_modal": round(100 - pct(modal_n, len(sub)), 1),
        "v2_trigger_normalized_entropy": round(entropy_norm(ct[c]), 3),
        "n_distinct_v2_triggers": len(ct[c]),
        "category_changed_pct": round(pct(sum(changed(p, V1_CATEGORY_FIELD) for p in sub), len(sub)), 1),
        "category_changed_to_outside_v1_vocab_pct": round(pct(sum(1 for p in sub if p["v2"][V1_CATEGORY_FIELD] not in V1_CAT_VOCAB), len(sub)), 1),
        "layer_changed_pct": round(pct(sum(changed(p, V1_LAYER_FIELD) for p in sub), len(sub)), 1),
        "subtype_changed_pct": round(pct(sum(changed(p, "primary_failure_subtype") for p in sub), len(sub)), 1),
        "v2_category_destinations": dict(collections.Counter(p["v2"][V1_CATEGORY_FIELD] for p in sub if changed(p, V1_CATEGORY_FIELD)).most_common(5)),
    }
overall_change = {f: round(pct(sum(changed(p, f) for p in P), len(P)), 1) for f in retained}
# category -> category migration (retained field), off-diagonal
cat_mig = collections.Counter((p["v1"][V1_CATEGORY_FIELD], p["v2"][V1_CATEGORY_FIELD]) for p in P if changed(p, V1_CATEGORY_FIELD))

# ---------- offsets ----------
def offs(sub):
    d = [p["v2"]["t_commit"] - p["n"] for p in sub]
    de = [p["v2"]["t_err"] - p["n"] for p in sub]
    N = len(sub)
    if N == 0:
        return {"N": 0}
    sd = sorted(d)
    pos = collections.Counter()
    for p in sub:
        n, te, tc = p["n"], p["v2"]["t_err"], p["v2"]["t_commit"]
        if n == tc and n == te: pos["n==t_err==t_commit"] += 1
        elif n == tc: pos["n==t_commit"] += 1
        elif n == te: pos["n==t_err"] += 1
        elif te < n < tc: pos["t_err<n<t_commit"] += 1
        elif n < te: pos["n<t_err"] += 1
        else: pos["n>t_commit"] += 1
    return {
        "N": N,
        "exact": sum(1 for x in d if x == 0), "exact_pct": round(pct(sum(1 for x in d if x == 0), N), 1),
        "within_1": sum(1 for x in d if abs(x) <= 1), "within_1_pct": round(pct(sum(1 for x in d if abs(x) <= 1), N), 1),
        "within_3": sum(1 for x in d if abs(x) <= 3), "within_3_pct": round(pct(sum(1 for x in d if abs(x) <= 3), N), 1),
        "beyond_5": sum(1 for x in d if abs(x) > 5), "beyond_5_pct": round(pct(sum(1 for x in d if abs(x) > 5), N), 1),
        "v2_later": sum(1 for x in d if x > 0), "v2_earlier": sum(1 for x in d if x < 0),
        "mean": round(sum(d) / N, 2), "median": sd[N // 2], "mean_abs": round(sum(abs(x) for x in d) / N, 2),
        "p10": sd[int(0.1 * N)], "p90": sd[min(N - 1, int(0.9 * N))],
        "t_err_minus_n_exact_pct": round(pct(sum(1 for x in de if x == 0), N), 1),
        "t_err_minus_n_within_3_pct": round(pct(sum(1 for x in de if abs(x) <= 3), N), 1),
        "n_position": dict(pos),
    }
hist = collections.Counter()
for p in P:
    x = p["v2"]["t_commit"] - p["n"]
    b = ("<-10" if x < -10 else "-10..-6" if x < -5 else "-5..-2" if x < -1 else "-1" if x == -1 else "0" if x == 0
         else "+1" if x == 1 else "+2..+5" if x <= 5 else "+6..+10" if x <= 10 else ">+10")
    hist[b] += 1
HB = ["<-10", "-10..-6", "-5..-2", "-1", "0", "+1", "+2..+5", "+6..+10", ">+10"]

m_eq = [p for p in P if p["v1_m"] == p["v2_m"]]
m_ne = [p for p in P if p["v1_m"] != p["v2_m"]]
by_scaffold = {s: offs([p for p in P if p["agent"] == s]) for s in sorted(set(p["agent"] for p in P))}
by_model = {s: offs([p for p in P if p["model"] == s]) for s in sorted(set(p["model"] for p in P))}
by_sm = {f"{s}/{mo}": offs([p for p in P if p["agent"] == s and p["model"] == mo])
         for s in sorted(set(p["agent"] for p in P)) for mo in sorted(set(p["model"] for p in P))}
chg_scaffold = {s: round(pct(sum(changed(p, V1_CATEGORY_FIELD) for p in P if p["agent"] == s), sum(1 for p in P if p["agent"] == s)), 1) for s in by_scaffold}
chg_model = {s: round(pct(sum(changed(p, V1_CATEGORY_FIELD) for p in P if p["model"] == s), sum(1 for p in P if p["model"] == s)), 1) for s in by_model}

# largest cells
cells = sorted(((c, t, ct[c][t]) for c in cats for t in ct[c]), key=lambda x: -x[2])

res = {
    "n_pairs_total": len(P_all), "n_pairs_fail_both": len(P), "excluded_v1_fail_v2_pass": odd,
    "v1_category_field": V1_CATEGORY_FIELD,
    "crosstab_counts": {c: {t: ct[c][t] for t in TRIG} for c in cats},
    "crosstab_row_pct": {c: {t: round(pct(ct[c][t], rowtot[c]), 1) for t in TRIG} for c in cats},
    "row_totals": rowtot, "col_totals": {t: coltot[t] for t in TRIG},
    "largest_cells": cells[:10],
    "per_v1_category": per_cat,
    "overall_change_rate_retained_fields_pct": overall_change,
    "category_to_category_migrations_top": [(a, b, n) for (a, b), n in cat_mig.most_common(10)],
    "category_change_rate_by_scaffold_pct": chg_scaffold, "category_change_rate_by_model_pct": chg_model,
    "offset_t_commit_minus_n": {"all": offs(P), "m_equal": offs(m_eq), "m_differs": offs(m_ne),
                                "histogram": {b: hist[b] for b in HB},
                                "by_scaffold": by_scaffold, "by_model": by_model, "by_scaffold_model": by_sm},
}
json.dump(res, open(os.path.join(OUT, "v1_to_v2_mapping.json"), "w"), indent=1, ensure_ascii=False)

# ---------- MD ----------
L = ["# v1 -> v2 mapping: categories, change rates, and single-marker offsets\n",
     "Generated by `resub/scripts/e6_mapping.py` from `v2_tasks/annotation_index*.json` (v1_annotation) and `traj_data_v2_all89tasks.json`.\n",
     f"Pairs with both a v1 object and a v2 record: {len(P_all)}. Of these {len(P)} are FAIL in v2 and are used below; "
     f"{len(odd)} pair(s) are `fail` in v1 but PASS in v2 and are excluded: {', '.join(f'`{c}`' for c in odd)}.\n",
     "## 1. v1 `primary_failure_category` x v2 `trigger_mechanism` (counts; row % in parentheses)\n"]
hdr = ["v1 category \\ v2 trigger"] + TRIG + ["row N"]
rows = []
for c in cats:
    rows.append([f"`{c}`"] + [f"{ct[c][t]} ({pct(ct[c][t], rowtot[c]):.0f}%)" if ct[c][t] else "0" for t in TRIG] + [rowtot[c]])
rows.append(["**col N**"] + [coltot[t] for t in TRIG] + [len(P)])
L.append(md_table(hdr, rows))
L.append("\n**Ten largest cells:** " + "; ".join(f"`{c}` -> `{t}` {n} ({pct(n, rowtot[c]):.0f}% of row)" for c, t, n in cells[:10]) + "\n")

L.append("## 2. Per-v1-category change / dispersion\n")
L.append("`dispersion` = 100 - modal v2-trigger share (how far the v1 category is from mapping to a single v2 trigger); `H_norm` = entropy over the 9 triggers / log 9. "
         "`cat changed` = share whose retained field `primary_failure_category` differs in v2 (any string change); `-> new vocab` = share whose v2 category is not one of the 11 v1 values.\n")
rows = [[f"`{c}`", d["n"], f"`{d['v2_trigger_modal']}` ({d['v2_trigger_modal_share']}%)", d["v2_trigger_dispersion_1_minus_modal"], d["v2_trigger_normalized_entropy"],
         d["n_distinct_v2_triggers"], d["category_changed_pct"], d["category_changed_to_outside_v1_vocab_pct"], d["layer_changed_pct"], d["subtype_changed_pct"]] for c, d in per_cat.items()]
L.append(md_table(["v1 category", "N", "modal v2 trigger", "dispersion %", "H_norm", "#triggers", "cat changed %", "-> new vocab %", "layer changed %", "subtype changed %"], rows))
L.append("\nOverall change rate on retained fields (exact string inequality, FAIL pairs): " + ", ".join(f"`{f}` {v}%" for f, v in overall_change.items()) + ".\n")
L.append("Largest v1 category -> v2 category migrations on the retained field: " + "; ".join(f"`{a}` -> `{b}` {n}" for a, b, n in res["category_to_category_migrations_top"][:8]) + ".\n")
L.append("Category change rate by scaffold: " + ", ".join(f"{k} {v}%" for k, v in chg_scaffold.items()) + ". By model: " + ", ".join(f"{k} {v}%" for k, v in chg_model.items()) + ".\n")

L.append("## 3. Offset of the v2 commitment step from the v1 single marker: d = t_commit - n\n")
def orow(name, o):
    if o["N"] == 0:
        return [name, 0] + ["-"] * 9
    return [name, o["N"], f"{o['exact']} ({o['exact_pct']}%)", f"{o['within_1']} ({o['within_1_pct']}%)", f"{o['within_3']} ({o['within_3_pct']}%)",
            f"{o['beyond_5']} ({o['beyond_5_pct']}%)", o["v2_earlier"], o["v2_later"], o["median"], o["mean"], o["mean_abs"]]
OH = ["subset", "N", "exact", "abs(d)<=1", "abs(d)<=3", "abs(d)>5", "v2 earlier (d<0)", "v2 later (d>0)", "median d", "mean d", "mean abs(d)"]
L.append(md_table(OH, [orow("all FAIL pairs", res["offset_t_commit_minus_n"]["all"]),
                       orow("v1 m == v2 m", res["offset_t_commit_minus_n"]["m_equal"]),
                       orow("v1 m != v2 m", res["offset_t_commit_minus_n"]["m_differs"])]))
L.append("\nHistogram of d (all FAIL pairs): " + ", ".join(f"{b}: {hist[b]}" for b in HB) + ".\n")
o = res["offset_t_commit_minus_n"]["all"]
L.append("Where the v1 marker sits relative to the v2 pair (t_err, t_commit): " + ", ".join(f"{k} {v} ({pct(v, o['N']):.1f}%)" for k, v in sorted(o["n_position"].items(), key=lambda kv: -kv[1])) + ".")
L.append(f"For reference, t_err - n is exact in {o['t_err_minus_n_exact_pct']}% and within +/-3 in {o['t_err_minus_n_within_3_pct']}% of pairs (t_commit is the closer v2 analogue of n, as the v2 prompt states).\n")
L.append("### 3.1 By scaffold\n")
L.append(md_table(OH, [orow(k, v) for k, v in by_scaffold.items()]))
L.append("\n### 3.2 By model\n")
L.append(md_table(OH, [orow(k, v) for k, v in by_model.items()]))
L.append("\n### 3.3 By scaffold x model\n")
L.append(md_table(OH, [orow(k, v) for k, v in by_sm.items() if v["N"]]))
L.append("\nMachine-readable version: `resub/e6/v1_to_v2_mapping.json`.\n")
open(os.path.join(OUT, "v1_to_v2_mapping.md"), "w").write("\n".join(L))
print("wrote v1_to_v2_mapping.md / .json")
