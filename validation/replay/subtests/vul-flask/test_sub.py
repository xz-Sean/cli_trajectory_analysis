# E4 sub-tests for vul-flask. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
# The vendored source tree is exercised in-process with /opt/venv/bin/python and PYTHONPATH=/app/flask_1.1.1/src
# (Werkzeug/Jinja2 are installed into /opt/venv by the official tests' setup.sh).
import hashlib, os, subprocess
from pathlib import Path
SRC = Path("/app/flask_1.1.1/src"); PY = "/opt/venv/bin/python"
PRISTINE_MD5 = {  # flask 1.1.1 release zip, src/flask/*.py
 "__init__.py": "709f6080961594a5bf0295a60a5d4987", "__main__.py": "af0923b2e216e7e4b54ac41a1e379b36",
 "_compat.py": "39d7af65ea397f98f0163a6c7ad9d2d8", "app.py": "184da4aea4e1db194ad898b632b32f94",
 "blueprints.py": "4cff4ebabbc071a309e5eca8edf17a57", "cli.py": "fb863444000142ae0fe14a06eaf93664",
 "config.py": "92fbd447b0f26d87f9f992717e805bae", "ctx.py": "d88a087361533efab769f072ad24554f",
 "debughelpers.py": "940a10eb87a4c37434e85dbef31cd36b", "globals.py": "2ca970199965227cf663353666100284",
 "helpers.py": "63c0353dea6627240445ee9271ea415a", "logging.py": "ba61abb7befa063f6577ec28af8e42e9",
 "sessions.py": "1c49780406d17dd7232397bbc89bc4c1", "signals.py": "76504f0b0194a2471391111929a071c7",
 "templating.py": "73e12ebeb27950f160aa6306d3de01bf", "testing.py": "0926a75b50ab82072c8a2d3568375243",
 "views.py": "985467723ba30d19b5d52719bd7cd43a", "wrappers.py": "0c1dadf9301aa10ddd9c5bbc51507186"}
PAYLOAD2 = ("{% for c in [].__class__.__base__.__subclasses__() %}{% if c.__name__ == 'catch_warnings' %}"
            "{% for b in c.__init__.__globals__.values() %}{% if b.__class__ == {}.__class__ %}{% if 'eval' in b.keys() %}"
            "{{ b['eval']('__import__(\"os\").popen(\"id\").read()') }}{% endif %}{% endif %}{% endfor %}{% endif %}{% endfor %}")
PROG = r'''
import sys, json
from flask import Flask, request, render_template_string
app = Flask(__name__)
@app.route("/")
def index():
    return render_template_string(request.args.get("name", "Hello"))
c = app.test_client()
print(json.dumps([c.get("/", query_string={"name": sys.argv[1]}).get_data(as_text=True)]))
'''

def _render(payload):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    r = subprocess.run([PY, "-c", PROG, payload], capture_output=True, text=True, timeout=40, env=env, cwd="/tmp")
    assert r.returncode == 0, r.stderr[-1200:]
    import json; return json.loads(r.stdout.strip().splitlines()[-1])[0]

def test_must_expression_not_evaluated():
    body = _render("{{233*233}}")
    assert "54289" not in body, body
    assert "{{233*233}}" in body, body          # echoed as plain text, not swallowed

def test_must_statement_blocks_not_executed():
    body = _render(PAYLOAD2)
    assert "root" not in body and "uid=" not in body, body
    assert "{%" in body and "%}" in body, body

def test_must_fix_lives_in_flask_codebase():
    changed = [f for f, md5 in PRISTINE_MD5.items()
               if not (SRC/"flask"/f).is_file() or hashlib.md5((SRC/"flask"/f).read_bytes()).hexdigest() != md5]
    assert changed, "no file under /app/flask_1.1.1/src/flask differs from the pristine 1.1.1 source"

def test_must_version_still_1_1_1():
    m = [l for l in (SRC/"flask/__init__.py").read_text().splitlines() if l.strip().startswith("__version__")]
    assert m and m[0].split("=", 1)[1].strip().strip("\"'") == "1.1.1", m

def test_mustnot_plain_text_rendering_broken():
    assert "Hello, World" in _render("Hello, World"), "plain input no longer echoed"

def test_mustnot_file_templates_broken():
    # framework must still render real (trusted) templates with context
    prog = r'''
import os, tempfile
from flask import Flask, render_template
d = tempfile.mkdtemp(); open(os.path.join(d, "t.html"), "w").write("v={{ x * 2 }}")
app = Flask(__name__, template_folder=d)
with app.app_context(): print(render_template("t.html", x=21))
'''
    r = subprocess.run([PY, "-c", prog], capture_output=True, text=True, timeout=40, cwd="/tmp",
                       env=dict(os.environ, PYTHONPATH=str(SRC)))
    assert r.returncode == 0 and r.stdout.strip().endswith("v=42"), (r.stdout[-200:], r.stderr[-800:])

# UNTESTED: none -- "user input treated as plain text" and "change inside /app/flask_1.1.1" are both covered above /
# by the official tests (the latter only indirectly, via the installed package's behaviour).
