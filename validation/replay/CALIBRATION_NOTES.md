# Sub-test calibration log

Rules: (1) oracle must pass all MUST / UNTESTED and violate no MUSTNOT; (2) every same-task PASS trajectory's final
state must pass; (3) at least one MUST must fail on the pristine image. Sub-tests failing (1) or (2) are dropped and listed here.

| task | sub-test | rule | outcome | reason |
|---|---|---|---|---|
| cpp-compatibility | test_must_compiles (v1, runtime-only) | 3 | rewritten | passed on pristine image because g++ accepts the C++14-style constexpr body when not used in a constant expression; now mirrors official constexpr usage |
| cpp-compatibility | test_untested_constexpr_usable | — | merged into must_compiles | redundant after rewrite |
| aimo-airline-departures | test_mustnot_results_hardcoded_without_script | 1 | dropped | oracle solution.sh writes results.txt directly; its airline_analysis.py does not regenerate it |
| aimo-airline-departures | test_untested_results_is_just_the_number | 1 | dropped | oracle's results.txt contains a multi-page proof; instruction says "just the number" — official tests only regex-search for 79. **Observation for the paper: the reference solution itself does not satisfy this stated requirement.** |
| bank-trans-filter | test_mustnot_unrelated_companies_included | — | skip-when-missing | mustnot checks are only meaningful once the output exists |
