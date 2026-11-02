#!/usr/bin/env python3
"""Recover Terminus2 keystrokes that the raw export dropped (command == "" but the model response
in agent_analysis contains {"commands": [{"keystrokes": ..., "duration": ...}]})."""
import json, re, sys, os, glob

def _json_candidates(text):
    """yield python objects parsed from `text`: whole text, fenced blocks, and the raw text of API wrappers"""
    try:
        obj = json.loads(text); yield obj
        # Gemini wrapper: candidates[].content.parts[].text ; OpenAI-style: choices[].message.content
        if isinstance(obj, dict):
            for cand in obj.get("candidates", []) or []:
                for part in (cand.get("content", {}) or {}).get("parts", []) or []:
                    if isinstance(part, dict) and "text" in part:
                        yield from _json_candidates(part["text"])
            for ch in obj.get("choices", []) or []:
                msg = (ch.get("message") or {}).get("content")
                if isinstance(msg, str): yield from _json_candidates(msg)
    except Exception:
        pass
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try: yield json.loads(m.group(1))
        except Exception: pass
    # bare object containing "commands": find first '{' before '"commands"' and try progressively
    i = text.find('"commands"')
    if i >= 0:
        start = text.rfind("{", 0, i)
        while start >= 0:
            depth = 0
            for j in range(start, len(text)):
                if text[j] == "{": depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        try: yield json.loads(text[start:j+1])
                        except Exception: pass
                        break
            start = text.rfind("{", 0, start)
            if start < 0 or i - start > 20000: break

def recover(agent_analysis):
    """return list of {"keystrokes": str, "duration": float} or None"""
    if not agent_analysis: return None
    for obj in _json_candidates(agent_analysis):
        if isinstance(obj, dict) and isinstance(obj.get("commands"), list):
            out = []
            for c in obj["commands"]:
                if isinstance(c, dict) and isinstance(c.get("keystrokes"), str):
                    out.append({"keystrokes": c["keystrokes"], "duration": float(c.get("duration") or 1.0)})
            return out
    # last resort: regex over escaped text
    ks = re.findall(r'\\*"keystrokes\\*"\s*:\s*\\*"((?:[^"\\]|\\.)*?)\\*"\s*,\s*\\*"duration\\*"\s*:\s*([\d.]+)', agent_analysis)
    if ks:
        out = []
        for k, d in ks:
            try: k = json.loads('"' + k.replace('\\\\', '\\') + '"')
            except Exception: k = k.encode().decode("unicode_escape")
            out.append({"keystrokes": k, "duration": float(d)})
        return out
    return None

if __name__ == "__main__":
    ROOT = os.environ.get("E4_ROOT", os.getcwd())
    import collections
    c = json.load(open(f"{ROOT}/trajrepair_extraction/corpus_RPO.json"))
    tot = collections.Counter(); rec = collections.Counter(); typed = collections.Counter(); typed_rec = collections.Counter()
    for task, t in c["tasks"].items():
        for cid, tr in t["trajectories"].items():
            if tr["scaffold"] != "terminus2": continue
            model = tr["model"]
            for s in tr["steps"]:
                if s["P"].get("action_type") != "empty": continue
                tot[model] += 1
                f = f"{ROOT}/merged_trajectories/{task}/terminus2/{model}/step_{s['i']}.jsonl"
                try: aa = json.load(open(f)).get("agent_analysis") or ""
                except Exception: continue
                r = recover(aa)
                shows = bool(re.search(r"^root@\S+:\S+# \S", s["O"].get("raw_output") or "", re.M))
                if shows: typed[model] += 1
                if r: 
                    rec[model] += 1
                    if shows: typed_rec[model] += 1
    print("model        empty  recovered  | typed-at-prompt  recovered-of-typed")
    for m in sorted(tot): print(f"{m:12s} {tot[m]:6d} {rec[m]:9d}  | {typed[m]:14d} {typed_rec[m]:18d}")
    print("TOTAL", sum(tot.values()), sum(rec.values()), "|", sum(typed.values()), sum(typed_rec.values()))
