#!/usr/bin/env python3
"""
build_oracle_batch.py — BRIDGE step (oracle_DESIGN.md §2). NO network / NO LLM calls.

Joins each (case_id, cut_step) in oracle_sample.jsonl to the raw trajectory transcript,
truncates the transcript to cut_step, strips the post-hoc "LLM Step Analysis" annotation
(so the oracle only sees what the agent itself produced), fills the FROZEN oracle prompt,
and emits one Anthropic Batch-API request per prefix.

Outputs:
    oracle_batch_requests.jsonl  one JSON request per line: {custom_id, params{...}}
                                 (exactly the shape submit_oracle_batch.py / the Batch API want)
    oracle_batch_map.json        custom_id -> {case_id, cut_step}  (rejoin after batch returns)

Run this now (cost-free). Then run submit_oracle_batch.py to actually call the model.

Usage:
    python3 build_oracle_batch.py \
        --sample oracle_sample.jsonl \
        --traj_root merged_trajectories \
        --out_requests oracle_batch_requests.jsonl \
        --out_map oracle_batch_map.json \
        [--max_output_chars 2000] [--preview case_id cut_step]
"""
import json, os, glob, argparse, re

# ─────────────────────────────────────────────────────────────────────────────
# MODEL — the oracle model. Frozen to Sonnet 4.6 for the whole experiment.
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 700          # output JSON is tiny; headroom so no JSON is truncated
TEMPERATURE = 0           # reproducibility (oracle_DESIGN.md §2)

# ─────────────────────────────────────────────────────────────────────────────
# FROZEN oracle prompt — verbatim from oracle_DESIGN.md §2. DO NOT edit casually:
# the experiment's validity depends on this being constant across all prefixes.
SYSTEM_BLOCK = """You are a monitor watching an AI coding agent work in a terminal, step by step. You are \
shown the task and the agent's actions SO FAR — a prefix of an in-progress run. You do \
NOT know how the run ends and must not assume the task is inherently hard.

Decide ONE thing: based ONLY on the steps shown, has the agent already entered an \
IRRECOVERABLE failing path — i.e., made and locked in a decisive error (wrong assumption, \
wrong target, abandoned requirement, corrupted state, ungrounded fabrication) that it \
shows no sign of recovering from within this prefix?

- Judge the trajectory's current state, not the task's difficulty. A hard task that the \
agent is still sensibly working through is NOT committed-to-failure.
- "Committed" means the decisive mistake is in place AND the agent is not actively, \
correctly recovering from it — not merely that something looks slightly off.
- Transient errors the agent is in the middle of debugging are NOT commitment.

Output JSON only:
{"committed": true|false,
 "confidence": 0.0-1.0,
 "decisive_step": <int or null: the step where commitment happened, if committed>,
 "evidence": "<≤25-word verbatim quote from the prefix>",
 "reason": "<one sentence>"}"""

# ─────────────────────────────────────────────────────────────────────────────
# CALIBRATED variant. Same task, same output schema, same anti-difficulty-leakage
# core — but the conservative version judged committed=true on only 3.7% of prefixes
# (17% recall even when the failure signal was already visible), because its three
# "do not over-call" caveats let the model excuse almost everything as "still
# debugging". This version REVERSES the burden of proof: a decisive error that is in
# place with no on-point correction shown == committed. Run alongside the conservative
# version as an ablation (sensitivity is a tunable operating point on the PR curve).
CALIBRATED_SYSTEM_BLOCK = """You are a monitor watching an AI coding agent work in a terminal, step by step. You are \
shown the task and the agent's actions SO FAR — a prefix of an in-progress run. You do \
NOT know how the run ends and must not assume the task is inherently hard.

Decide ONE thing: based ONLY on the steps shown, has the agent already entered an \
IRRECOVERABLE failing path — i.e., made and locked in a decisive error (wrong assumption, \
wrong target, abandoned requirement, corrupted state, ungrounded fabrication) and, within \
the steps shown, taken NO concrete, on-point action to correct that specific error?

How to judge:
- Judge the trajectory's current state, not the task's difficulty. Do not penalize an agent \
that is still sensibly and correctly working a hard task.
- A decisive error IS committed-to-failure once it is in place AND the agent is not, in the \
shown steps, actively and correctly fixing THAT error. Continued activity that does not \
target the decisive error — more commands, new sub-tasks, cosmetic edits, re-running the \
same broken thing — is NOT recovery.
- Treat these as committed even if the agent looks busy: fabricating outputs / results / \
URLs / benchmark numbers, hard-coding or faking artifacts, abandoning or substituting away \
a required component, giving up behind a hollow placeholder, or proceeding on a clearly \
false premise the agent never rechecks.
- A transient error counts as NOT committed ONLY if the agent has visibly recognized it and \
is taking a targeted corrective step within the shown prefix. Debugging in circles, or not \
yet noticing, does NOT earn the benefit of the doubt.
- When a decisive error is in place and you see no on-point correction in the prefix, lean \
committed=true; set confidence by how clearly the error is locked in.

Output JSON only, no preamble:
{"committed": true|false,
 "confidence": 0.0-1.0,
 "decisive_step": <int or null: the step where commitment happened, if committed>,
 "evidence": "<≤25-word verbatim quote from the prefix>",
 "reason": "<one sentence>"}"""

PROMPTS = {"conservative": SYSTEM_BLOCK, "calibrated": CALIBRATED_SYSTEM_BLOCK}

def user_block(task, prefix_transcript, requirements=None):
    head = f"Task:\n{task}"
    if requirements:
        # inject the task's core requirements ONLY (no difficulty label — keeps the
        # §4 anti-difficulty-leakage guard). Gives the monitor the spec it needs to
        # catch spec-relative failures (abandoned/violated requirement).
        head += "\nCore requirements:\n" + "\n".join(f"- {r}" for r in requirements)
    return f"{head}\n\nAgent steps so far (1..t):\n{prefix_transcript}"

# ─────────────────────────────────────────────────────────────────────────────
def parse_id(cid):
    t, a, m = cid.split("__")
    return t, a, m

def truncate_output(text, cap):
    """Keep head+tail of long terminal output; mark the elision. Controls token cost."""
    if text is None:
        return ""
    text = text.rstrip()
    if len(text) <= cap:
        return text
    head = int(cap * 0.66)
    tail = cap - head
    return (text[:head] + f"\n...[{len(text) - cap} chars omitted]...\n" + text[-tail:])

# Strip the post-hoc "## LLM Step Analysis" block when falling back to markdown.
_LLM_ANALYSIS_RE = re.compile(r"\n-{3,}\s*\n##\s*LLM Step Analysis.*\Z", re.DOTALL)

def load_step(traj_dir, n, max_output_chars):
    """Return (command, reasoning, output) for step n, preferring the structured .jsonl.
    NEVER includes the post-hoc llm_analysis."""
    jp = f"{traj_dir}/step_{n}.jsonl"
    if os.path.exists(jp):
        o = json.load(open(jp))
        cmd = (o.get("command") or "").rstrip()
        reasoning = (o.get("agent_analysis") or "").rstrip()
        out = truncate_output(o.get("terminal_result"), max_output_chars)
        return cmd, reasoning, out
    # fallback: parse markdown, dropping the LLM Step Analysis section
    mp = f"{traj_dir}/step_{n}.md"
    raw = open(mp).read()
    raw = _LLM_ANALYSIS_RE.sub("", raw)
    def section(name):
        m = re.search(rf"##\s*{name}\s*\n(.*?)(?=\n##\s|\Z)", raw, re.DOTALL)
        return m.group(1).strip() if m else ""
    cmd = section("Command").strip("`").replace("bash\n", "", 1).strip()
    reasoning = section("Agent's Analysis")
    out = truncate_output(section("Terminal Output").strip("`"), max_output_chars)
    return cmd, reasoning, out

def build_prefix(traj_dir, cut_step, max_output_chars):
    blocks = []
    for n in range(1, cut_step + 1):
        cmd, reasoning, out = load_step(traj_dir, n, max_output_chars)
        b = [f"[Step {n}]"]
        if cmd:
            b.append("$ " + cmd)
        if reasoning:
            b.append("Reasoning: " + reasoning)
        b.append("Output:")
        b.append(out if out else "(no output)")
        blocks.append("\n".join(b))
    return "\n\n".join(blocks)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="oracle_sample.jsonl")
    ap.add_argument("--traj_root", default="merged_trajectories")
    ap.add_argument("--variant", choices=list(PROMPTS), default="calibrated",
                    help="which frozen prompt to use")
    ap.add_argument("--task_field", choices=["slug", "spec"], default="slug",
                    help="slug = task name only; spec = name + core requirements")
    ap.add_argument("--task_spec_path",
                    default="data/merged_tasks.json",
                    help="merged_tasks.json providing core_requirements_summary per task_id")
    ap.add_argument("--out_requests", default=None,
                    help="default: oracle_batch_requests_<variant>[_spec].jsonl")
    ap.add_argument("--out_map", default=None,
                    help="default: oracle_batch_map_<variant>[_spec].json")
    ap.add_argument("--max_output_chars", type=int, default=2000,
                    help="cap per-step terminal output (head+tail kept); controls token cost")
    ap.add_argument("--max_tokens", type=int, default=MAX_TOKENS,
                    help="output token cap per call (700 avoids truncated JSON)")
    ap.add_argument("--preview", nargs=2, metavar=("CASE_ID", "CUT"), default=None,
                    help="print one fully-assembled prompt and exit (no files written)")
    args = ap.parse_args()

    sysblock = PROMPTS[args.variant]
    suffix = f"_{args.variant}" + ("_spec" if args.task_field == "spec" else "")
    out_requests = args.out_requests or f"oracle_batch_requests{suffix}.jsonl"
    out_map = args.out_map or f"oracle_batch_map{suffix}.json"

    # task requirements (only loaded for the spec variant)
    reqmap = {}
    if args.task_field == "spec":
        for t in json.load(open(args.task_spec_path)):
            reqmap[t["task_id"]] = t.get("core_requirements_summary") or []

    lines = [json.loads(l) for l in open(args.sample) if l.strip()]

    # preview mode: assemble a single prompt and print it, then stop
    if args.preview:
        cid, cut = args.preview[0], int(args.preview[1])
        task, agent, model = parse_id(cid)
        traj_dir = f"{args.traj_root}/{task}/{agent}/{model}"
        prefix = build_prefix(traj_dir, cut, args.max_output_chars)
        ub = user_block(task, prefix, reqmap.get(task))
        print("=" * 70 + f"\nSYSTEM ({args.variant}):\n" + "=" * 70)
        print(sysblock)
        print("\n" + "=" * 70 + f"\nUSER  (case={cid} cut={cut}):\n" + "=" * 70)
        print(ub)
        print("\n" + "=" * 70)
        print(f"approx tokens: system {len(sysblock)//4}, user {len(ub)//4}")
        return

    requests, cmap = [], {}
    est_in_chars = 0
    skipped = []
    for i, r in enumerate(lines):
        cid, cut = r["case_id"], r["cut_step"]
        task, agent, model = parse_id(cid)
        traj_dir = f"{args.traj_root}/{task}/{agent}/{model}"
        try:
            prefix = build_prefix(traj_dir, cut, args.max_output_chars)
        except Exception as e:
            skipped.append(f"{cid}@{cut}: {e}")
            continue
        ub = user_block(task, prefix, reqmap.get(task))
        est_in_chars += len(sysblock) + len(ub)
        custom_id = f"p{i:05d}"
        cmap[custom_id] = {"case_id": cid, "cut_step": cut}
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": args.max_tokens,
                "temperature": TEMPERATURE,
                "system": sysblock,
                "messages": [{"role": "user", "content": ub}],
            },
        })

    with open(out_requests, "w") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
    json.dump(cmap, open(out_map, "w"), indent=0)

    # rough cost estimate (Sonnet 4.6 Batch = 50% off: $1.50 / Mtok in, $7.50 / Mtok out)
    in_tok = est_in_chars / 4
    out_tok = len(requests) * args.max_tokens * 0.3   # outputs are short; assume ~30% of cap
    cost = in_tok / 1e6 * 1.50 + out_tok / 1e6 * 7.50
    print(f"variant={args.variant}")
    print(f"built {len(requests)} batch requests -> {out_requests}")
    print(f"custom_id map -> {out_map}")
    print(f"est input tokens ~{in_tok/1e6:.2f}M, est output tokens ~{out_tok/1e6:.2f}M")
    print(f"est BATCH cost (Sonnet 4.6, 50% off): ${cost:.2f}  (full price ~${cost*2:.2f})")
    if skipped:
        print(f"SKIPPED {len(skipped)}:")
        for s in skipped[:10]:
            print("  ", s)
    print(f"\nmodel={MODEL} temperature={TEMPERATURE} max_tokens={args.max_tokens} "
          f"variant={args.variant} task_field={args.task_field}")
    print(f"NEXT: submit with --requests {out_requests} --map {out_map} "
          f"--out oracle_calls{suffix}.jsonl")

if __name__ == "__main__":
    main()
