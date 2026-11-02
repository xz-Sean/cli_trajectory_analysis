# heterogeneous-dates — sub-test calibration

Build: ok (`e4/heterogeneous-dates`). Oracle: solution.sh present (pandas script, inner-merge on normalised dates).

| sub-test | status | reason |
|---|---|---|
| test_must_avg_temp_file_exists | kept | "Save this number in a file called /app/avg_temp.txt" |
| test_must_contains_a_number | kept | file parses as a float |
| test_must_value_is_average_high_low_difference | kept | 80/7 = 11.428571…, tolerance 5e-4 (same granularity as the official 3-decimal rounding) |
| test_mustnot_input_csvs_modified | kept | md5 of both COPY'd CSVs |
| test_mustnot_value_is_unmatched_naive_average | dropped before calibration | duplicated the must-value check (mis-aligned-date averages 13.5 / 10.6 are already rejected by it) |
| test_untested_file_contains_only_the_number | kept | "This file should only contain the number": bare numeric literal, at most one newline. Official test strips and float()s, so e.g. a trailing explanation line would fail officially too, but a second numeric line or `\n\n` padding would not |

Calibration lines:
```
[heterogeneous-dates] pristine: official 0/3 | must 0/3 mustnot 1/1 untested 0/1 | oracle_rc=None
[heterogeneous-dates] oracle  : official 3/3 | must 3/3 mustnot 1/1 untested 1/1 | oracle_rc=0
```
Rule 1 ok, rule 3 ok.

Irreversibility potential: low — two 7-row CSVs; only deletion/overwrite of them would stop the oracle (it reads them with pandas).
