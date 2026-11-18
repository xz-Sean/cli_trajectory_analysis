# Raw trajectories

The step-by-step logs of the 1,794 runs analyzed in the paper, one archive per agent scaffold.

| Archive | Runs | Files | Size |
|---|---|---|---|
| `merged_trajectories_miniswe.tar.gz` | 614 | 32,766 | 19 MB |
| `merged_trajectories_openhands.tar.gz` | 618 | 46,308 | 18 MB |
| `merged_trajectories_terminus2.tar.gz` | 562 | 49,272 | 15 MB |

Uncompressed, the three archives hold 128,346 files (about 720 MB) covering 63,276 steps.
The archives are distributed compressed because the logs quote Terminal-Bench task material, which
carries the benchmark's canary string and should not be published as plain, crawlable text.

## Extracting

Run from the package root, so that the scripts in `validation/` find the data at their default path:

```bash
shasum -a 256 -c raw_trajectories/SHA256SUMS      # run inside raw_trajectories/, or adjust the paths
for f in raw_trajectories/merged_trajectories_*.tar.gz; do tar -xzf "$f"; done
```

This creates `merged_trajectories/` with the layout

```
merged_trajectories/<task>/<scaffold>/<model>/
    summary.md        task id, trial name, outcome, list of steps
    step_<k>.jsonl    one JSON object: task_id, step_index, command, agent_analysis, terminal_result
                      (+ llm_analysis, raw_llm_response where available)
    step_<k>.md       the same step rendered as Markdown
```

A run with annotation id `<task>__<scaffold>__<model>` in `data/traj_data_v2_all89tasks.json` is
stored in `merged_trajectories/<task>/<scaffold>/<model>/`.

- 89 tasks; scaffolds `miniswe`, `openhands`, `terminus2`; models `claude`, `deepseek-v3.2`,
  `devstral`, `gemini`, `gpt5`, `kimi`, `qwen`.
- Only the 1,794 runs with a recorded outcome are included. The 66 runs that exist but have no
  recorded outcome are not part of the analysis and are not released.

## Redaction

The runs were executed on machines whose names and network details are not relevant to the study.
Before release, these infrastructure identifiers were replaced by fixed placeholders. Nothing else
was changed: every `step_<k>.jsonl` line parses to the same JSON structure as before redaction.

| Placeholder | Replaces |
|---|---|
| `REDACTED_HOST` | host names of the execution machines |
| `REDACTED_PROXY`, `PORT` | the outbound HTTP proxy and its port |
| `REDACTED_DOMAIN` | domain names in proxy exclusion lists |
| `REDACTED_IP`, `REDACTED_IPV6`, `REDACTED_MAC` | addresses of the execution machines' network interfaces |
| `5.14.0-REDACTED.x86_64` | the host kernel build string |
| `REDACTED_PATH` | the storage path in the `session_file` field of `summary.md` |

Redaction touched 1,865 of the 128,346 files. Where a host name had been broken across two lines by
terminal wrapping, the placeholder is followed by the original line break.

The same placeholders appear in a few quoted snippets under `data/` and `validation/`.

## Known limitations of the logs

- OpenHands logs do not record the payload of file-editing tool calls, so OpenHands file edits
  cannot be re-executed (this is why the replay in `validation/replay/` uses MiniSWE and Terminus2).
- Credentials that appear in the logs are task fixtures (for example the AWS documentation example
  key) or keys generated inside the disposable task container.

License: CC BY 4.0 (see `LICENSE-DATA`).
