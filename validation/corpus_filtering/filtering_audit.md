# E7 task-filtering audit

Pinned Terminal-Bench checkout: 241 tasks with `task.yaml` (see `resub/tb_tasks/TB_COMMIT.txt`). Retained (paper) tasks: 89; dropped: 152. All 89 retained tasks exist in the pinned checkout. Raw `category` strings: 26 distinct; after normalising obvious spelling variants (game->games, math->mathematics, file_operations->file-operations): 23. Difficulty levels: 3 (hard, easy, medium).

## Category distribution (task level, normalised categories)

| category | all tasks | retained 89 | dropped | retention rate |
|---|---|---|---|---|
| software-engineering | 47 | 16 | 31 | 34% |
| system-administration | 26 | 8 | 18 | 31% |
| security | 22 | 6 | 16 | 27% |
| data-science | 20 | 11 | 9 | 55% |
| scientific-computing | 18 | 4 | 14 | 22% |
| file-operations | 17 | 7 | 10 | 41% |
| debugging | 17 | 5 | 12 | 29% |
| mathematics | 14 | 5 | 9 | 36% |
| model-training | 13 | 8 | 5 | 62% |
| games | 11 | 4 | 7 | 36% |
| machine-learning | 9 | 5 | 4 | 56% |
| data-processing | 8 | 2 | 6 | 25% |
| algorithms | 6 | 3 | 3 | 50% |
| personal-assistant | 3 | 1 | 2 | 33% |
| data-querying | 2 | 0 | 2 | 0% |
| reproducible-builds | 1 | 0 | 1 | 0% |
| research | 1 | 1 | 0 | 100% |
| computer-vision | 1 | 0 | 1 | 0% |
| optimization | 1 | 1 | 0 | 100% |
| protocol-analysis | 1 | 0 | 1 | 0% |
| audio-processing | 1 | 1 | 0 | 100% |
| file-system | 1 | 0 | 1 | 0% |
| video-processing | 1 | 1 | 0 | 100% |
| **total** | 241 | 89 | 152 | 37% |

Categories present in the benchmark but absent from the retained set: computer-vision, data-querying, file-system, protocol-analysis, reproducible-builds (18 of 23 normalised categories retained).

Category chi-square retained vs dropped (descriptive only, 26/46 cells have expected < 5): chi2 = 22.51, dof = 22, p = 0.43.

## Difficulty distribution (task level)

| difficulty | all tasks | retained 89 | dropped | retention rate |
|---|---|---|---|---|
| easy | 64 | 22 | 42 | 34% |
| medium | 120 | 37 | 83 | 31% |
| hard | 57 | 30 | 27 | 53% |
| share hard | 23.7% | 33.7% | 17.8% | |

Chi-square test of independence, difficulty x (retained, dropped): chi2 = 8.128, dof = 2, p = 0.0172 (manual), p = 0.0172 (scipy); Cramer's V = 0.184. Expected counts retained: [23.6, 44.3, 21.0], dropped: [40.4, 75.7, 36.0].

## Trajectory accounting

| stage | count | note |
|---|---|---|
| full grid 89 x 3 x 7 | 1869 | paper: 1869 |
| leaves present locally | 1860 | 9 grid cells have no trajectory at source |
| analysed records | 1794 | paper: 1794 (1184 FAIL + 610 PASS; paper 1184+610) |
| present but excluded | 66 | by is_resolved: {'Unknown': 9, 'None': 57} |
| missing + excluded | 75 | paper says 75 unavailable: EQUAL |

### The missing grid cells (no trajectory at source)

- install-windows-xp__miniswe__devstral
- install-windows-xp__miniswe__gemini
- leelachess0-pytorch-conversion__miniswe__devstral
- leelachess0-pytorch-conversion__miniswe__gemini
- leelachess0-pytorch-conversion__openhands__devstral
- leelachess0-pytorch-conversion__openhands__gemini
- leelachess0-pytorch-conversion__terminus2__devstral
- leelachess0-pytorch-conversion__terminus2__gemini
- play-zork-easy__openhands__gemini

### Present-but-excluded leaves

`summary.md` carries only `is_resolved` (True/False/None/Unknown); no timeout/abnormal-termination field exists in the local export, so the reason is recorded as the missing verdict. `agent_submitted` is a heuristic available only for mini-swe-agent, whose transcript contains an explicit COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT command (True = agent ended normally; False = transcript ends without a submit, consistent with a step/time cap or harness abort). The local export of terminus2/openhands does not preserve the agent completion flag, so it is None there.

By scaffold: {'miniswe': 5, 'terminus2': 59, 'openhands': 2}; by model: {'devstral': 5, 'deepseek-v3.2': 20, 'gpt5': 22, 'qwen': 6, 'claude': 4, 'kimi': 5, 'gemini': 4}; agent_submitted: {'True': 5, 'None': 61}.

Excluded by task: solve-maze-challenge (10), chem-rf (4), hf-train-lora-adapter (4), leelachess0-pytorch-conversion (4), reshard-c4-data (4), stable-parallel-kmeans (4), hf-lora-adapter (3), speech-to-text (3), constraints-scheduling (2), fix-ocaml-gc (2), install-windows-3.11 (2), install-windows-xp (2), mahjong-winninghand (2), mteb-retrieve (2), multi-source-data-merger (2), puzzle-solver (2), pytorch-model-cli (2), sam-cell-seg (2), train-fasttext (2), triton-interpret (2), video-processing (2), winning-avg-corewars (2), portfolio-optimization (1), spinning-up-rl (1)

| case_id | is_resolved | steps | agent_submitted | last command | reason |
|---|---|---|---|---|---|
| chem-rf__miniswe__devstral | Unknown | 49 | True | `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | no outcome recorded (is_resolved=Unknown) |
| chem-rf__terminus2__deepseek-v3.2 | None | 90 | None | `cat > /app/fit_model.py << 'EOF'` | no outcome recorded (is_resolved=None) |
| chem-rf__terminus2__gpt5 | None | 11 | None | `wc -l /app/fit_model.py` | no outcome recorded (is_resolved=None) |
| chem-rf__terminus2__qwen | None | 80 | None | `N/A` | no outcome recorded (is_resolved=None) |
| constraints-scheduling__terminus2__deepseek-v3.2 | None | 28 | None | `tail -10 /app/meeting_scheduled.ics` | no outcome recorded (is_resolved=None) |
| constraints-scheduling__terminus2__gpt5 | None | 6 | None | `cat /app/meeting_scheduled.ics` | no outcome recorded (is_resolved=None) |
| fix-ocaml-gc__terminus2__deepseek-v3.2 | None | 179 | None | `make -j4 2>&1 \| tee build9.log \| head -150` | no outcome recorded (is_resolved=None) |
| fix-ocaml-gc__terminus2__gpt5 | None | 297 | None | `make -C testsuite one DIR=tests/basic` | no outcome recorded (is_resolved=None) |
| hf-lora-adapter__terminus2__deepseek-v3.2 | None | 54 | None | `ls -la /app/merged_model/` | no outcome recorded (is_resolved=None) |
| hf-lora-adapter__terminus2__gpt5 | None | 11 | None | `cat /app/detection_results.json` | no outcome recorded (is_resolved=None) |
| hf-lora-adapter__terminus2__qwen | None | 30 | None | `echo "Task completed successfully!"` | no outcome recorded (is_resolved=None) |
| hf-train-lora-adapter__terminus2__claude | None | 48 | None | `echo "=== Final Verification ==="` | no outcome recorded (is_resolved=None) |
| hf-train-lora-adapter__terminus2__deepseek-v3.2 | None | 127 | None | `echo 'Task completed. Outputs generated.'` | no outcome recorded (is_resolved=None) |
| hf-train-lora-adapter__terminus2__gpt5 | None | 111 | None | `sed -n '1,200p' /app/lora_results.json` | no outcome recorded (is_resolved=None) |
| hf-train-lora-adapter__terminus2__qwen | None | 88 | None | `N/A` | no outcome recorded (is_resolved=None) |
| install-windows-3.11__terminus2__deepseek-v3.2 | None | 202 | None | `dpkg --force-depends -i qemu-system-x86_*.deb 2>&1 \| tail -10` | no outcome recorded (is_resolved=None) |
| install-windows-3.11__terminus2__gpt5 | None | 485 | None | `echo "Access the web interface at: http://$(hostname -I \| awk '{print $1}')/vnc.` | no outcome recorded (is_resolved=None) |
| install-windows-xp__terminus2__deepseek-v3.2 | None | 144 | None | `echo 'Admin account will be: tb-admin (created via unattended answer file)'` | no outcome recorded (is_resolved=None) |
| install-windows-xp__terminus2__gpt5 | None | 337 | None | `ps -ef \| grep -E '[q]emu-system-i386\|websockify'` | no outcome recorded (is_resolved=None) |
| leelachess0-pytorch-conversion__terminus2__deepseek-v3.2 | None | 200 | None | `python3 /app/lc0utils.py 2>&1` | no outcome recorded (is_resolved=None) |
| leelachess0-pytorch-conversion__terminus2__gpt5 | None | 29 | None | `python3 - << 'PY'` | no outcome recorded (is_resolved=None) |
| leelachess0-pytorch-conversion__terminus2__kimi | None | 26 | None | `echo "=== Final Verification ==="` | no outcome recorded (is_resolved=None) |
| leelachess0-pytorch-conversion__terminus2__qwen | None | 34 | None | `exit` | no outcome recorded (is_resolved=None) |
| mahjong-winninghand__terminus2__deepseek-v3.2 | None | 30 | None | `wc -l result.txt` | no outcome recorded (is_resolved=None) |
| mahjong-winninghand__terminus2__gpt5 | None | 5 | None | `cat /app/result.txt` | no outcome recorded (is_resolved=None) |
| mteb-retrieve__terminus2__deepseek-v3.2 | None | 36 | None | `` | no outcome recorded (is_resolved=None) |
| mteb-retrieve__terminus2__gpt5 | None | 8 | None | `cat /app/result.txt` | no outcome recorded (is_resolved=None) |
| multi-source-data-merger__terminus2__deepseek-v3.2 | None | 23 | None | `ls -lh /app/merged_users.parquet /app/conflicts.json` | no outcome recorded (is_resolved=None) |
| multi-source-data-merger__terminus2__gpt5 | None | 6 | None | `python3 - << 'PY'` | no outcome recorded (is_resolved=None) |
| portfolio-optimization__terminus2__deepseek-v3.2 | None | 31 | None | `python3 final_check.py` | no outcome recorded (is_resolved=None) |
| puzzle-solver__terminus2__deepseek-v3.2 | None | 32 | None | `# ensure we have layer files for each depth 0..max depth` | no outcome recorded (is_resolved=None) |
| puzzle-solver__terminus2__gpt5 | None | 17 | None | `python3 - << 'PY'` | no outcome recorded (is_resolved=None) |
| pytorch-model-cli__terminus2__gpt5 | None | 16 | None | `printf "prediction.txt contents: '"; cat prediction.txt; printf "'\n"` | no outcome recorded (is_resolved=None) |
| pytorch-model-cli__terminus2__kimi | None | 74 | None | `./cli_tool weights.json image.png` | no outcome recorded (is_resolved=None) |
| reshard-c4-data__terminus2__claude | None | 37 | None | `ls -la *.py pyproject.toml` | no outcome recorded (is_resolved=None) |
| reshard-c4-data__terminus2__deepseek-v3.2 | None | 126 | None | `echo 'All tests passed.'` | no outcome recorded (is_resolved=None) |
| reshard-c4-data__terminus2__gpt5 | None | 107 | None | `echo "Sample chunk files:" && find /app/resharded_check -type f -name '*.chunk' ` | no outcome recorded (is_resolved=None) |
| reshard-c4-data__terminus2__kimi | None | 30 | None | `python3 compress.py` | no outcome recorded (is_resolved=None) |
| sam-cell-seg__terminus2__deepseek-v3.2 | None | 103 | None | `ls -l /app/final_output.csv` | no outcome recorded (is_resolved=None) |
| sam-cell-seg__terminus2__gpt5 | None | 4 | None | `sed -n '1,120p' /app/convert_masks.py` | no outcome recorded (is_resolved=None) |
| solve-maze-challenge__miniswe__devstral | Unknown | 47 | True | `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | no outcome recorded (is_resolved=Unknown) |
| solve-maze-challenge__miniswe__gemini | Unknown | 14 | True | `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | no outcome recorded (is_resolved=Unknown) |
| solve-maze-challenge__openhands__devstral | Unknown | 45 | None | `ls -la /app/ && cat /app/test_results.json 2>/dev/null \|\| echo "No results file ` | no outcome recorded (is_resolved=Unknown) |
| solve-maze-challenge__openhands__gemini | Unknown | 36 | None | `C-c` | no outcome recorded (is_resolved=Unknown) |
| solve-maze-challenge__terminus2__claude | None | 67 | None | `cat solution.js` | no outcome recorded (is_resolved=None) |
| solve-maze-challenge__terminus2__devstral | Unknown | 71 | None | `` | no outcome recorded (is_resolved=Unknown) |
| solve-maze-challenge__terminus2__gemini | Unknown | 31 | None | `` | no outcome recorded (is_resolved=Unknown) |
| solve-maze-challenge__terminus2__gpt5 | None | 303 | None | `sed -n '1,200p' /app/test_results.json` | no outcome recorded (is_resolved=None) |
| solve-maze-challenge__terminus2__kimi | None | 79 | None | `cat solution.js` | no outcome recorded (is_resolved=None) |
| solve-maze-challenge__terminus2__qwen | None | 42 | None | `C-c` | no outcome recorded (is_resolved=None) |
| speech-to-text__terminus2__deepseek-v3.2 | None | 193 | None | `wget -O /tmp/ffmpeg.tar.xz 'https://github.com/BtbN/FFmpeg-Builds/releases/downl` | no outcome recorded (is_resolved=None) |
| speech-to-text__terminus2__gpt5 | None | 108 | None | `` | no outcome recorded (is_resolved=None) |
| speech-to-text__terminus2__qwen | None | 57 | None | `cat > /app/output.txt << 'EOF'` | no outcome recorded (is_resolved=None) |
| spinning-up-rl__miniswe__devstral | Unknown | 58 | True | `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | no outcome recorded (is_resolved=Unknown) |
| stable-parallel-kmeans__miniswe__gemini | Unknown | 20 | True | `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | no outcome recorded (is_resolved=Unknown) |
| stable-parallel-kmeans__terminus2__claude | None | 37 | None | `N/A` | no outcome recorded (is_resolved=None) |
| stable-parallel-kmeans__terminus2__gpt5 | None | 7 | None | `python3 test_implementation.py` | no outcome recorded (is_resolved=None) |
| stable-parallel-kmeans__terminus2__kimi | None | 56 | None | `C-cC-cC-c` | no outcome recorded (is_resolved=None) |
| train-fasttext__terminus2__deepseek-v3.2 | None | 160 | None | `echo 'done?'` | no outcome recorded (is_resolved=None) |
| train-fasttext__terminus2__gpt5 | None | 163 | None | `if [ -f /app/model.bin ]; then ./fastText/fasttext test /app/model.bin work/vali` | no outcome recorded (is_resolved=None) |
| triton-interpret__terminus2__deepseek-v3.2 | None | 60 | None | `head -30 /app/triton_agent_sol.py` | no outcome recorded (is_resolved=None) |
| triton-interpret__terminus2__gpt5 | None | 56 | None | `N/A` | no outcome recorded (is_resolved=None) |
| video-processing__terminus2__deepseek-v3.2 | None | 44 | None | `# finalize` | no outcome recorded (is_resolved=None) |
| video-processing__terminus2__gpt5 | None | 10 | None | `cat /app/output.toml` | no outcome recorded (is_resolved=None) |
| winning-avg-corewars__terminus2__deepseek-v3.2 | None | 105 | None | `diff my_warrior.red warriors/snake.red` | no outcome recorded (is_resolved=None) |
| winning-avg-corewars__terminus2__gpt5 | None | 223 | None | `pmars -b -r 100 -f my_warrior.red warriors/g2-clear.red` | no outcome recorded (is_resolved=None) |

### Consistency check: summary.md `is_resolved` vs analysed label

{'True->PASS': 610, 'False->FAIL': 1178, 'None->FAIL': 6}

6 analysed records are labelled FAIL although `summary.md` has no verdict (is_resolved=None): add-benchmark-lm-eval-harness__terminus2__deepseek-v3.2, add-benchmark-lm-eval-harness__terminus2__gpt5, add-benchmark-lm-eval-harness__terminus2__kimi, add-benchmark-lm-eval-harness__terminus2__qwen, build-pov-ray__terminus2__deepseek-v3.2, build-pov-ray__terminus2__gpt5. These were kept in the 1,794 while the 66 above were dropped; the paper's 'failed execution' boundary is therefore not exactly the `is_resolved is None/Unknown` boundary.


### Per scaffold x model

| scaffold | model | grid | leaves | missing | excluded | analysed |
|---|---|---|---|---|---|---|
| miniswe | claude | 89 | 89 | 0 | 0 | 89 |
| miniswe | deepseek-v3.2 | 89 | 89 | 0 | 0 | 89 |
| miniswe | gpt5 | 89 | 89 | 0 | 0 | 89 |
| miniswe | kimi | 89 | 89 | 0 | 0 | 89 |
| miniswe | qwen | 89 | 89 | 0 | 0 | 89 |
| miniswe | devstral | 89 | 87 | 2 | 3 | 84 |
| miniswe | gemini | 89 | 87 | 2 | 2 | 85 |
| openhands | claude | 89 | 89 | 0 | 0 | 89 |
| openhands | deepseek-v3.2 | 89 | 89 | 0 | 0 | 89 |
| openhands | gpt5 | 89 | 89 | 0 | 0 | 89 |
| openhands | kimi | 89 | 89 | 0 | 0 | 89 |
| openhands | qwen | 89 | 89 | 0 | 0 | 89 |
| openhands | devstral | 89 | 88 | 1 | 1 | 87 |
| openhands | gemini | 89 | 87 | 2 | 1 | 86 |
| terminus2 | claude | 89 | 89 | 0 | 4 | 85 |
| terminus2 | deepseek-v3.2 | 89 | 89 | 0 | 20 | 69 |
| terminus2 | gpt5 | 89 | 89 | 0 | 22 | 67 |
| terminus2 | kimi | 89 | 89 | 0 | 5 | 84 |
| terminus2 | qwen | 89 | 89 | 0 | 6 | 83 |
| terminus2 | devstral | 89 | 88 | 1 | 1 | 87 |
| terminus2 | gemini | 89 | 88 | 1 | 1 | 87 |

The 3,843/5,040 raw completion pool (pre-filter, all 240 tasks) is not available locally; per scaffold x model raw completion rates cannot be recomputed here.

