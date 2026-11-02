"""E6 shared loaders (stdlib only). Read-only: never writes to the data files."""
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # package root
OUT = os.path.join(ROOT, "validation", "codebook_history")
INDEX_GLOB = os.path.join(ROOT, "data", "v1_annotations", "annotation_index*.json")
V2_FILE = os.path.join(ROOT, "data", "traj_data_v2_all89tasks.json")
DATA_355 = os.path.join(ROOT, "data", "v1_annotations", "completed_traj_data.json")
DATA_826 = os.path.join(ROOT, "data", "v1_annotations", "completed_traj_data_merged_with_repaired.json")

V1_CATEGORY_FIELD = "primary_failure_category"
V1_LAYER_FIELD = "primary_failure_layer"


def norm_outcome(o):
    s = str(o).lower()
    if s in ("true", "pass"):
        return "pass"
    if s in ("false", "fail"):
        return "fail"
    raise ValueError(o)


def load_index():
    items = []
    for f in sorted(glob.glob(INDEX_GLOB)):
        items += json.load(open(f))
    for it in items:
        it["_outcome"] = norm_outcome(it["outcome"])
        it["_index_file"] = None
    return items


def load_v2():
    recs = json.load(open(V2_FILE))
    return {r["case_id"]: r for r in recs}


def load_data_files():
    return json.load(open(DATA_355)), json.load(open(DATA_826))


def v1_n(ann):
    return ann["command_index_ratio"].get("n")


def v1_m(ann):
    return ann["command_index_ratio"].get("m")


def is_fail_v2(rec):
    return "t_err" in rec


def pairs():
    """Records with both a v1_annotation and a v2 record. Returns list of dicts."""
    idx = load_index()
    v2 = load_v2()
    out = []
    for it in idx:
        a = it["v1_annotation"]
        if not a:
            continue
        r = v2[it["case_id"]]
        out.append({
            "case_id": it["case_id"],
            "v1_case_id": it["v1_case_id"],
            "task_id": it["task_id"],
            "agent": it["agent"],
            "model": it["model"],
            "index_outcome": it["_outcome"],
            "v1": a,
            "v2": r,
            "n": v1_n(a),
            "v1_m": v1_m(a),
            "v2_m": r["m"],
            "v2_fail": is_fail_v2(r),
        })
    return out


def pct(x, d):
    return 0.0 if d == 0 else 100.0 * x / d


def md_table(header, rows):
    lines = ["| " + " | ".join(str(h) for h in header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)
