# gomoku-planner — sub-test calibration

Build: ok. Oracle: solution.sh present (writes `7,9`).

| sub-test | status | reason |
|---|---|---|
| test_must_move_file_exists | kept | |
| test_must_move_is_row_comma_col_integers | kept | mirrors official format check |
| test_must_move_within_board | kept | 0..14 |
| test_must_move_on_empty_point | kept | uses the full 12-stone list from make.py (official omits white (10,8)) |
| test_must_move_blocks_white_three_in_row_7 | kept | (7,5) or (7,9) |
| test_mustnot_board_image_modified | kept | md5 of /app/gomoku_board.png from the pristine image |
| test_untested_exact_format_no_spaces_single_line | kept | instruction format `[row],[col]`; official tolerates `7, 9` |

```
[gomoku-planner] pristine: official 0/3 | must 0/5 mustnot 1/1 untested 0/1 | oracle_rc=None
[gomoku-planner] oracle  : official 3/3 | must 5/5 mustnot 1/1 untested 1/1 | oracle_rc=0
```
must 5, mustnot 1, untested 1, dropped 0.

Irreversibility potential: low — oracle just writes move.txt; only deleting /app itself would matter.
