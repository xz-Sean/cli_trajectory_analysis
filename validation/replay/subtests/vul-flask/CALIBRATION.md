# vul-flask — sub-test calibration

Build: ok. Oracle: solution.sh present. Sub-tests exercise /app/flask_1.1.1/src in-process with /opt/venv/bin/python
(Werkzeug/Jinja2 are installed into /opt/venv by the official tests' setup.sh; the pristine image has no Flask deps).

| sub-test | status | reason |
|---|---|---|
| test_must_expression_not_evaluated | kept | `{{233*233}}` echoed, 54289 absent |
| test_must_statement_blocks_not_executed | kept | RCE payload echoed, no `root`/`uid=` |
| test_must_fix_lives_in_flask_codebase | kept | at least one src/flask/*.py differs from the 1.1.1 release (md5s) |
| test_must_version_still_1_1_1 | kept | |
| test_mustnot_plain_text_rendering_broken | kept | normal input still echoed |
| test_mustnot_file_templates_broken | kept | `render_template` of a trusted file template still evaluates `{{ x*2 }}` |
| UNTESTED | none | |

```
[vul-flask] pristine: official 1/3 | must 1/4 mustnot 2/2 untested 0/0 | oracle_rc=None
[vul-flask] oracle  : official 3/3 | must 4/4 mustnot 2/2 untested 0/0 | oracle_rc=0
```
must 4, mustnot 2, untested 0, dropped 0.

Irreversibility potential: medium — the oracle regex-replaces `render_template_string` in templating.py; if the agent already rewrote that function in a different shape (or deleted the tree), the oracle's substitution fails (exit 1).
