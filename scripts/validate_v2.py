#!/usr/bin/env python3
"""validate_v2.py — full consistency validator for the v2/v2.1 annotation file.
Usage: python3 validate_v2.py <annotations.json>
Exit code 0 iff zero violations. Prints per-check counts and offending case_ids.
"""
import json, sys
from collections import defaultdict

STD_FAB = {"direct_fabrication", "proxy_or_shortcut",
           "fake_artifact_or_execution", "false_completion_or_validation"}
CODES = set("EPWXVRCO")

def seg_problems(r):
    m, seg = r["m"], sorted(r["action_segments"])
    if not seg: return "empty"
    if seg[0][0] != 1: return f"starts_at_{seg[0][0]}"
    if seg[-1][1] != m: return f"ends_at_{seg[-1][1]}_m_{m}"
    for (s, e, c) in seg:
        if s > e: return f"inverted_{s}_{e}"
        if c not in CODES: return f"bad_code_{c}"
    for i in range(len(seg) - 1):
        if seg[i+1][0] <= seg[i][1]: return f"overlap_at_{seg[i+1][0]}"
        if seg[i+1][0] != seg[i][1] + 1: return f"gap_{seg[i][1]}_to_{seg[i+1][0]}"
    return None

def main(path):
    data = json.load(open(path))
    fail = [r for r in data if "t_commit" in r]
    pas  = [r for r in data if "t_commit" not in r]
    V = defaultdict(list)

    for r in fail:
        c, m = r["case_id"], r["m"]
        if not (1 <= r["t_err"] <= m): V["C1_t_err_range"].append(c)
        if not (1 <= r["t_commit"] <= m): V["C2_t_commit_range"].append(c)
        if r["t_err"] > r["t_commit"]: V["C3_err_after_commit"].append(c)
        if r["t_surface"] is not None and not (r["t_err"] <= r["t_surface"] <= m):
            V["C4_t_surface_invalid"].append(c)
        if r["forewarning_present"]:
            if r["forewarning_first_step"] is None or not r["forewarning_types"]:
                V["C5a_forewarn_missing_data"].append(c)
            elif not (1 <= r["forewarning_first_step"] < r["t_commit"]):
                V["C5b_forewarn_not_before_commit"].append(c)
        else:
            if r["forewarning_first_step"] is not None or r["forewarning_types"]:
                V["C5c_forewarn_false_but_data"].append(c)
        if r["awareness"] == "never_aware":
            if r["first_awareness_step"] is not None: V["C6a_neveraware_with_step"].append(c)
        else:
            s = r["first_awareness_step"]
            if s is None or not (r["t_err"] <= s <= m): V["C6b_awareness_step_invalid"].append(c)
        if r["fabrication_present"]:
            if r["fabrication_type"] not in STD_FAB: V["C7a_fabtype_nonstandard"].append(c)
            if r["fabrication_onset_step"] is None or not (1 <= r["fabrication_onset_step"] <= m):
                V["C7b_fab_onset_invalid"].append(c)
        else:
            if r["fabrication_type"] or r["fabrication_onset_step"] or r["fabrication_evidence"]:
                V["C7c_fab_false_but_data"].append(c)
        if r["verification_ever"]:
            s = r["first_relevant_verification_step"]
            if s is None or not (1 <= s <= m): V["C8a_verif_step_invalid"].append(c)
        elif r["first_relevant_verification_step"] is not None:
            V["C8b_verif_false_with_step"].append(c)
        if r["trigger_mechanism"] == "other" and not r["trigger_mechanism_other"]:
            V["C9_other_no_text"].append(c)
        p = seg_problems(r)
        if p: V["C10_segments_fail"].append((c, p))

    for r in pas:
        c, m = r["case_id"], r["m"]
        p = seg_problems(r)
        if p: V["C11_segments_pass"].append((c, p))
        if r["num_error_events"] > 0:
            s = r["first_error_step"]
            if s is None or not (1 <= s <= m): V["C12_first_error_invalid"].append(c)
        elif r["first_error_step"] is not None:
            V["C13_no_errors_with_step"].append(c)
        if r["num_recoveries"] > r["num_error_events"]:
            V["C14_recoveries_gt_errors"].append(c)
        if r["verification_before_claim"]:
            s = r["first_relevant_verification_step"]
            if s is None or not (1 <= s <= m): V["C15_verif_step_invalid"].append(c)
        if r["near_miss"] and not r["near_miss_description"]: V["C16a_nearmiss_no_desc"].append(c)
        if r["suspicious_pass"] and not r["suspicious_pass_evidence"]: V["C16b_suspass_no_evidence"].append(c)

    total = sum(len(v) for v in V.values())
    print(f"records: {len(data)} (fail {len(fail)}, pass {len(pas)}) | violations: {total}")
    for k in sorted(V):
        print(f"  {k}: {len(V[k])}")
        for item in V[k][:5]:
            print(f"      {item}")
        if len(V[k]) > 5: print(f"      ... +{len(V[k]) - 5} more")
    sys.exit(0 if total == 0 else 1)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/traj_data_v2_all89tasks.json")
