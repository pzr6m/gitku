"""The website's JavaScript engine must count and score exactly like the Python package."""

import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gitku.syllables import OVERRIDES

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

REFERENCE = """
import json, sys
sys.path.insert(0, "src")
from gitku.syllables import count_word
from gitku.haiku import tokenize, find_windows
from gitku.sources import clean_message

data = json.load(sys.stdin)
out = {"words": {w: count_word(w) for w in data["words"]}, "texts": [], "clean": []}
for t in data["texts"]:
    toks = tokenize(t)
    out["texts"].append({
        "tokens": [[x.text, x.core, x.syllables] for x in toks],
        "strict": [[list(w.lines), w.score] for w in find_windows(toks, True)],
        "loose": [[list(w.lines), w.start, w.end, w.score] for w in find_windows(toks, False)],
    })
for m in data["messages"]:
    out["clean"].append(clean_message(m))
print(json.dumps(out))
"""

HAND_PICKED = (
    "build broken nobody touched config table file little example makes jumped wanted tried "
    "studied doing playing actual violin region social function variable database deployment "
    "parser silence again refactoring timeout hello world queue quiet science business idea "
    "isn't don't it's I'd doesn't can't won't aren't couldn't y'all rock'n'roll v2 foo.py x86 "
    "100% a/b pdf wtf pr ci api API Config constructor hasOwnProperty __proto__ toString"
).split()


def sample_words():
    rng = random.Random(1234)
    letters = "abcdefghijklmnopqrstuvwxyz"
    random_words = ["".join(rng.choice(letters) for _ in range(rng.randint(1, 12))) for _ in range(600)]
    return sorted(set(HAND_PICKED + list(OVERRIDES) + random_words))


TEXTS = [
    "the build is broken nobody touched the config and yet here we are",
    "An old silent pond, a frog jumps into the pond, splash! Silence again.",
    "Note: the build is broken nobody touched the config and yet here we are. Moving on to other things now.",
    "The logs are quiet, the pager sleeps through the night, and nobody weeps.",
    "Cleaned up retries. The logs are quiet, the pager sleeps through the night, and nobody weeps.",
    "fix v2 parser and the foo.py module so it stops crashing on empty input please",
    "- *quiet* morning light — settles on the sleeping town; coffee warms my hands",
    "stop the retry loop before it eats the whole queue or we all lose sleep",
    "go go go go go go go go go go go go go go go go go",
    "“Never” trust the cache, it lies to you when you least expect it again",
    "snake_case well-known e.g. rock'n'roll isn't it's I'd",
    "",
    "   ",
]

MESSAGES = [
    "feat(parser): handle empty input\n\ndetails here\nhttps://example.com/issue/1\n"
    "Signed-off-by: A <a@b.c>\nCo-Authored-By: B <b@c.d>\n",
    "fix!: drop python 3.8\n\nClaude-Session: https://claude.ai/code/session_x\n",
    "the old cache is gone\nwe cleared it out of our disks\nspace returns to us\n",
    "Merge branch 'main'\n\n   \n",
    "chore: \n",
]


def run(cmd, payload, env=None):
    proc = subprocess.run(
        cmd, input=json.dumps(payload), capture_output=True, text=True, cwd=ROOT, env=env, check=True
    )
    return json.loads(proc.stdout)


def test_javascript_matches_python():
    payload = {"words": sample_words(), "texts": TEXTS, "messages": MESSAGES}
    env = dict(os.environ, GITKU_NO_CMUDICT="1", PYTHONPATH=str(ROOT / "src"))
    expected = run([sys.executable, "-c", REFERENCE], payload, env=env)
    actual = run([NODE, str(ROOT / "tests" / "web" / "reference.js")], payload)

    bad_words = {w: (expected["words"][w], actual["words"][w])
                 for w in expected["words"] if expected["words"][w] != actual["words"][w]}
    assert not bad_words, f"syllable counts differ (python, js): {bad_words}"
    assert actual["clean"] == expected["clean"]
    for text, exp, act in zip(TEXTS, expected["texts"], actual["texts"]):
        assert act == exp, f"results differ for {text!r}"
