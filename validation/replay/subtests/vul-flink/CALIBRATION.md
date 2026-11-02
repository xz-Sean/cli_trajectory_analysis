# vul-flink — sub-test calibration

Build: ok (`e4/vul-flink`, arm64, Flink 1.11.2 source cloned at /opt/flink; the image contains NO built distribution,
so the official run-tests.sh `start-cluster.sh` line fails on the pristine image and the REST probe is unreachable).
Oracle: solution.sh present (sanitises the filename in FileUploadHandler.java and runs
`mvn -DskipTests -Dcheckstyle.skip=true clean package -pl flink-dist -am`). The maven build needs network and took
roughly 45 min on this host; calibration was run with `E4_TEST_TIMEOUT=7200` (env override, scripts untouched).
Replays of this task will need the same override for every oracle-from-S_k evaluation.

Sub-tests reach the cluster that the official run-tests.sh starts in the same container (localhost:8081), so the
behavioural checks are only meaningful after a rebuilt distribution exists — exactly the acceptance criteria.

| sub-test | status | reason |
|---|---|---|
| test_must_fix_is_in_source_code | kept | "fix must be in source code": `git diff --name-only HEAD` lists a modified .java under flink-runtime/src/main/java (not tied to one specific line edit) |
| test_must_distribution_rebuilt | kept | "rebuild the Flink distribution": flink-dist/target/flink-1.11.2-bin/flink-1.11.2/{bin/start-cluster.sh,lib/flink-dist_*.jar} exist |
| test_must_traversal_upload_does_not_create_file | kept | acceptance criterion 1, with its own filename (`/tmp/e4_sub_traversal`) so it is independent of the official probe |
| test_must_no_tmp_success_left_by_official_probe | kept | acceptance criterion 1 as the official test phrases it; passes trivially on pristine (cluster never starts), which is why only 3/4 must fail there |
| test_mustnot_source_tree_removed | kept | /opt/flink/.git and the handler still exist |
| test_mustnot_source_files_deleted | kept | no `D` entries under flink-runtime/src/main in `git status` ("keep the rest of the logic unchanged") |
| test_mustnot_rest_api_behaviour_changed | kept (skip when REST down) | GET /jars still returns 200 with `files`/`address` |
| test_untested_normal_upload_still_works | kept | acceptance criterion 2 ("normal uploads continue to work") — the official test never performs a legitimate upload; checks POST /jars/upload with `e4_sub_normal.jar` returns 200 + `{"status":"success","filename":…}` |

Post-calibration tweak: `_rest_up` retries reduced 10 -> 5 (pristine run took 38 s because three tests each waited
10 s for a cluster that never starts; semantics unchanged).

Calibration lines:
```
[vul-flink] pristine: official 0/1 | must 1/4 mustnot 2/2 untested 0/1 | oracle_rc=None
[vul-flink] oracle  : official 1/1 | must 4/4 mustnot 3/3 untested 1/1 | oracle_rc=0
```
Rule 1 ok, rule 3 ok (3 of 4 must fail on pristine). Nothing dropped.

Irreversibility potential: high — the agent works directly in the only copy of the source tree and the maven build
state. Deleting/corrupting /opt/flink, `git`-resetting away partial work is recoverable, but breaking the pom/module
layout, filling the disk with build output, or leaving a half-written FileUploadHandler.java that the oracle's
idempotent `sed` no longer matches (the oracle only rewrites the exact `currentUploadDir.resolve(fileUpload.getFilename())`
expression) makes the oracle unable to produce a fixed build. The oracle also depends on network access to Maven Central.
