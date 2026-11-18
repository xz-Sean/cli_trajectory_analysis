#!/usr/bin/env python3
"""RQ4 Tables IV & V: pass-rate grid and epistemic-share grid over the 21 model x scaffold
systems. Reproduces Table IV (pass rate) and Table V (% epistemic among failures)."""
import json, csv, argparse
from collections import defaultdict

EPI = {"false_premise", "misread_output", "ignored_signal", "spec_neglect", "premature_action"}
SCAF = ["miniswe", "openhands", "terminus2"]
SC_NAME = {"miniswe": "MiniSWE", "openhands": "OpenHands", "terminus2": "Terminus2"}
# paper column order + data-key mapping
MODELS = [("GPT-5", "gpt5"), ("Claude", "claude"), ("Devstral", "devstral"),
          ("DeepSeek", "deepseek-v3.2"), ("Kimi", "kimi"), ("Qwen", "qwen"), ("Gemini", "gemini")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", default="data/traj_data_v2_all89tasks.json")
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()
    recs = [r for r in json.load(open(a.data)) if r.get("schema_version") == "v2"]
    cell = defaultdict(list)
    for r in recs:
        _, sc, mo = r["case_id"].split("__")
        cell[(sc, mo)].append(r)

    def passrate(sc, mo):
        c = cell[(sc, mo)]; f = [r for r in c if "t_commit" in r]
        return 100 * (1 - len(f) / len(c)) if c else float("nan")
    def epi(sc, mo):
        f = [r for r in cell[(sc, mo)] if "t_commit" in r]
        return 100 * sum(r["trigger_mechanism"] in EPI for r in f) / len(f) if f else float("nan")

    for tag, fn, fname in [("Table IV — pass rate (%)", passrate, "table4_pass_grid.csv"),
                           ("Table V — epistemic share of failures (%)", epi, "table5_epistemic_grid.csv")]:
        print(f"\n=== {tag} ===")
        hdr = ["Scaffold"] + [m for m, _ in MODELS]
        print("  " + "".join(f"{h:>10}" for h in hdr))
        rows = [hdr]
        for sc in SCAF:
            row = [SC_NAME[sc]] + [round(fn(sc, k)) for _, k in MODELS]
            rows.append(row)
            print("  " + f"{SC_NAME[sc]:>10}" + "".join(f"{v:>9}%" for v in row[1:]))
        with open(f"{a.outdir}/{fname}", "w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        print(f"  wrote {a.outdir}/{fname}")

if __name__ == "__main__":
    main()
