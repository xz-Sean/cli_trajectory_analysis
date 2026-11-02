# E4 sub-tests for count-dataset-tokens. State assertions only.
# MUST = explicit instruction requirements; MUSTNOT = prohibited/implicit constraints;
# UNTESTED = required by instruction but not covered by official tests.
import os, re, subprocess, pytest
from pathlib import Path
ANS = Path("/app/answer.txt"); EXPECTED = "79586"

def _text():
    if not ANS.exists(): pytest.skip("no answer.txt yet")
    return ANS.read_text()

# ---------------- MUST ----------------
def test_must_answer_file_exists():
    assert ANS.is_file() and ANS.stat().st_size > 0

def test_must_answer_contains_correct_count():
    assert re.search(rf"(?<!\d){EXPECTED}(?!\d)", _text())

# ---------------- MUSTNOT ----------------
def test_mustnot_answer_without_tokenizer_on_disk():
    # the count must come from the Qwen2.5-1.5B-Instruct tokenizer; a correct number with no trace of that tokenizer
    # anywhere on the filesystem means it was pasted in, not computed
    _text()
    r = subprocess.run("find / -xdev \\( -path /proc -o -path /sys -o -path /dev \\) -prune -o \\( -type f -o -type l \\) "
                       "\\( -name tokenizer.json -o -name tokenizer_config.json -o -name vocab.json \\) -print 2>/dev/null",
                       shell=True, capture_output=True, text=True, timeout=50)
    hits = [l for l in r.stdout.splitlines() if "qwen2.5-1.5b" in l.lower() or "qwen2_5-1.5b" in l.lower()]
    assert hits, "no Qwen2.5-1.5B-Instruct tokenizer files found on disk"

# ---------------- UNTESTED ----------------
def test_untested_answer_is_bare_integer():
    # "write the integer number of tokens without spaces or commas" -> file is just the number
    assert _text().strip() == EXPECTED, repr(_text()[:200])
