# mahjong-winninghand — sub-test calibration

Build: ok (`e4/mahjong-winninghand`). Oracle: solution.sh present (writes /app/mahjong_checker.py and runs it).

| sub-test | status | reason |
|---|---|---|
| test_must_result_exists | kept | "Write results … to result.txt in /app" |
| test_must_every_input_file_has_exactly_one_result_line | kept | one `hand_NNN.json: …` line per input file, no duplicates |
| test_must_winning_pattern_sets_correct | kept | per-file pattern sets for the 7 winning hands (mirrors official expected set, but per file) |
| test_must_non_winning_hand_reported | kept | hand_003 must be `{ "Not a winning hand" }` |
| test_mustnot_input_hands_modified | kept | md5 of protected/hand_00[1-8].json (COPY'd read-only inputs) |
| test_mustnot_extra_or_unknown_files_in_result | kept (skip when no output) | result must not list files that do not exist |
| test_untested_exact_line_format | kept | brace-enclosed, double-quoted, comma-separated set — official test only regex-extracts quoted strings, so `hand_001.json: Seven Pairs, Standard` style output would pass officially only through its fallback; exact format is untested |
| test_untested_pattern_labels_use_required_wording | kept | only the four wordings from the instruction may appear (official exact-set compare covers this implicitly for correct files; kept as a stand-alone format check) |

Calibration lines:
```
[mahjong-winninghand] pristine: official 0/2 | must 0/4 mustnot 1/1 untested 0/2 | oracle_rc=None
[mahjong-winninghand] oracle  : official 2/2 | must 4/4 mustnot 2/2 untested 2/2 | oracle_rc=0
```
Rule 1 ok, rule 3 ok. Nothing dropped.

Irreversibility potential: low — the inputs are 8 tiny read-only JSON files; an agent would have to delete them (root can) for the oracle to fail, and the oracle only needs them to exist.
