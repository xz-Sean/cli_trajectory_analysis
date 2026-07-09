#!/usr/bin/env python3
"""
submit_oracle_batch.py — THE PAID LLM STEP. Submits the prepared prefixes to the
Anthropic Message Batches API (Sonnet 4.6, temperature 0), polls to completion, parses
each result's JSON, and writes oracle_calls.jsonl for score_oracle.py.

Prerequisites:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Inputs:
    oracle_batch_requests.jsonl  (from build_oracle_batch.py)
    oracle_batch_map.json        (custom_id -> {case_id, cut_step})

Output:
    oracle_calls.jsonl           one line per prefix:
                                 {case_id, cut_step, committed, confidence,
                                  decisive_step, evidence, reason}

Usage:
    # create + poll + fetch in one go:
    python3 submit_oracle_batch.py
    # or resume fetching a batch already created earlier:
    python3 submit_oracle_batch.py --batch_id msgbatch_xxx
    # build-only sanity (no submit): validates the request file parses
    python3 submit_oracle_batch.py --dry_run
"""
import json, argparse, time, os, sys, re

def load_requests(path):
    return [json.loads(l) for l in open(path) if l.strip()]

def extract_json(text):
    """Pull the oracle's JSON object out of the model text. Robust to ``` fences,
    trailing prose, and — critically — braces/quotes INSIDE the evidence string.
    The old naive brace-counter miscounted on evidence that quotes code (e.g.
    "${value}" or an unescaped quote) and silently dropped valid judgments to
    'unparsed', systematically under-counting recall."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE).strip()
    start = t.find("{")
    if start < 0:
        return None
    # 1) proper JSON decode from the first '{' — understands strings, ignores trailing prose
    try:
        obj, _ = json.JSONDecoder().raw_decode(t[start:])
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # 2) fallback: regex-extract the 3 decision fields even if evidence/reason broke the JSON
    out = {}
    m = re.search(r'"committed"\s*:\s*(true|false)', t, re.IGNORECASE)
    if m:
        out["committed"] = m.group(1).lower() == "true"
    m = re.search(r'"confidence"\s*:\s*([0-9]*\.?[0-9]+)', t)
    if m:
        out["confidence"] = float(m.group(1))
    m = re.search(r'"decisive_step"\s*:\s*(null|\d+)', t, re.IGNORECASE)
    if m:
        out["decisive_step"] = None if m.group(1).lower() == "null" else int(m.group(1))
    return out if "committed" in out else None

def normalize(obj):
    """Coerce oracle output into the scorer's expected fields with safe defaults."""
    if not isinstance(obj, dict):
        return {"committed": False, "confidence": 0.0, "decisive_step": None,
                "evidence": None, "reason": "unparseable"}
    committed = bool(obj.get("committed", False))
    try:
        conf = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    ds = obj.get("decisive_step")
    ds = ds if isinstance(ds, int) else None
    return {"committed": committed, "confidence": conf, "decisive_step": ds,
            "evidence": obj.get("evidence"), "reason": obj.get("reason")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", default="oracle_batch_requests.jsonl")
    ap.add_argument("--map", default="oracle_batch_map.json")
    ap.add_argument("--out", default="oracle_calls.jsonl")
    ap.add_argument("--batch_id", default=None, help="resume an existing batch instead of creating one")
    ap.add_argument("--poll", type=int, default=30, help="seconds between status polls")
    ap.add_argument("--dry_run", action="store_true", help="validate request file, do not submit")
    args = ap.parse_args()

    reqs = load_requests(args.requests)
    cmap = json.load(open(args.map))
    print(f"loaded {len(reqs)} requests, {len(cmap)} custom_ids")

    if args.dry_run:
        bad = [r for r in reqs if "custom_id" not in r or "params" not in r]
        miss = [r["custom_id"] for r in reqs if r["custom_id"] not in cmap]
        print(f"dry-run OK: malformed {len(bad)}, custom_ids missing from map {len(miss)}")
        print(f"model={reqs[0]['params']['model']} temp={reqs[0]['params']['temperature']} "
              f"max_tokens={reqs[0]['params']['max_tokens']}")
        return

    try:
        import anthropic
    except ModuleNotFoundError:
        sys.exit("ERROR: `pip install anthropic` first.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: set ANTHROPIC_API_KEY in the environment first.")

    client = anthropic.Anthropic()

    batch_id = args.batch_id
    if not batch_id:
        # Anthropic SDK accepts the same {custom_id, params} dicts we wrote.
        batch = client.messages.batches.create(requests=reqs)
        batch_id = batch.id
        print(f"created batch {batch_id}  (status {batch.processing_status})")
        print(f"  -> save this id; you can resume with --batch_id {batch_id}")
    else:
        print(f"resuming batch {batch_id}")

    # poll
    while True:
        b = client.messages.batches.retrieve(batch_id)
        counts = b.request_counts
        print(f"  [{b.processing_status}] succeeded={counts.succeeded} "
              f"errored={counts.errored} processing={counts.processing} "
              f"canceled={counts.canceled} expired={counts.expired}")
        if b.processing_status == "ended":
            break
        time.sleep(args.poll)

    # fetch + parse results
    n_ok, n_err, n_unparsed = 0, 0, 0
    with open(args.out, "w") as fout:
        for res in client.messages.batches.results(batch_id):
            cid = res.custom_id
            meta = cmap.get(cid, {})
            rec = {"case_id": meta.get("case_id"), "cut_step": meta.get("cut_step")}
            if res.result.type == "succeeded":
                msg = res.result.message
                text = "".join(blk.text for blk in msg.content if getattr(blk, "type", "") == "text")
                obj = extract_json(text)
                if obj is None:
                    n_unparsed += 1
                rec.update(normalize(obj))
            else:
                n_err += 1
                rec.update(normalize(None))
                rec["reason"] = f"batch_result_{res.result.type}"
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_ok += 1

    print(f"wrote {n_ok} results -> {args.out}  (errored {n_err}, unparsed-json {n_unparsed})")
    print("NEXT: python3 score_oracle.py --sample oracle_sample.jsonl "
          f"--calls {args.out} --out results/oracle_results.json")

if __name__ == "__main__":
    main()
