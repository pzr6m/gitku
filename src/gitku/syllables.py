"""Syllable counting for English words and developer jargon.

Lookup order for a word:

1. ``OVERRIDES`` - hand-checked counts for tech terms and words the heuristic
   gets wrong (``api``, ``config``, ``create`` ...).
2. The CMU Pronouncing Dictionary, if the optional ``cmudict`` package is
   installed (``pip install gitku[accurate]``).
3. A rule-based heuristic that needs no dependencies.

Set ``GITKU_NO_CMUDICT=1`` to skip step 2.
"""

from __future__ import annotations

import os
import re

# Counts for words that neither a dictionary nor the heuristic reliably gets
# right. Mostly developer vocabulary, plus a few common troublemakers.
OVERRIDES = {
    # developer vocabulary
    "git": 1, "github": 2, "gitlab": 2, "api": 3, "apis": 3, "cli": 3, "clis": 3,
    "ci": 2, "cd": 2, "cpu": 3, "gpu": 3, "ui": 2, "ux": 2, "gui": 2, "ide": 3,
    "id": 2, "ids": 2, "json": 2, "yaml": 2, "toml": 2, "html": 4, "http": 4,
    "https": 5, "ios": 3, "npm": 3, "pypi": 3, "pip": 1, "nginx": 2, "regex": 2,
    "config": 2, "configs": 2, "repo": 2, "repos": 2, "async": 2, "readme": 2,
    "todo": 2, "todos": 2, "fixme": 2, "wip": 3, "typo": 2, "typos": 2,
    "lint": 1, "linter": 2, "linters": 2, "bugfix": 2, "hotfix": 2, "refactor": 3,
    "refactors": 3, "refactored": 3, "refactoring": 4, "stdin": 3, "stdout": 3,
    "stderr": 3, "utf": 3, "ascii": 3, "aws": 3, "gcp": 3, "vm": 2, "ok": 2,
    "os": 2, "ip": 2, "ssh": 3, "dns": 3, "tcp": 3, "tls": 3, "ssl": 3,
    "cron": 1, "env": 2, "dev": 1, "prod": 1, "init": 2, "args": 2, "param": 2,
    "params": 2, "impl": 3, "util": 2, "utils": 2, "dir": 1, "dirs": 1,
    "src": 3, "lib": 1, "libs": 1, "bool": 1, "enum": 2, "struct": 1,
    "mutex": 2, "sudo": 2, "vim": 1, "emacs": 2, "bash": 1, "zsh": 3,
    "kubernetes": 4, "docker": 2, "dockerfile": 3, "makefile": 3, "webpack": 2,
    "backend": 2, "frontend": 2, "middleware": 3, "namespace": 3, "localhost": 3,
    "username": 3, "metadata": 4, "boolean": 3, "plugin": 2, "plugins": 2,
    "changelog": 3, "workflow": 2, "workflows": 2, "runtime": 2, "codebase": 3,
    # common words the heuristic fumbles
    "create": 2, "created": 3, "creates": 2, "creating": 3, "creation": 3,
    "idea": 3, "ideas": 3, "area": 3, "areas": 3, "being": 2, "science": 2,
    "quiet": 2, "poem": 2, "poems": 2, "poet": 2, "poetry": 3, "client": 2,
    "clients": 2, "every": 2, "different": 3, "business": 2, "average": 3,
    "camera": 3, "chocolate": 3, "comfortable": 3, "evening": 2, "interesting": 3,
    "favorite": 3, "favourite": 3, "general": 3, "memory": 3, "hour": 1,
    "hours": 1, "our": 1, "fire": 1, "wire": 1, "tired": 1, "higher": 2,
    "lion": 2, "violin": 3, "real": 1, "really": 2, "queue": 1, "queues": 1,
    "the": 1, "are": 1, "were": 1, "one": 1, "once": 1, "two": 1, "eye": 1,
    "eyes": 1, "people": 2, "whole": 1, "above": 2, "love": 1, "done": 1,
    "video": 3, "videos": 3,
}

_CMU: dict | None = None
_CMU_TRIED = False


def _cmu() -> dict | None:
    """Lazily load the CMU dictionary, if available and not disabled."""
    global _CMU, _CMU_TRIED
    if _CMU_TRIED:
        return _CMU
    _CMU_TRIED = True
    if os.environ.get("GITKU_NO_CMUDICT"):
        return None
    try:
        import cmudict  # type: ignore

        _CMU = cmudict.dict()
    except Exception:  # missing package or corrupt data: fall back silently
        _CMU = None
    return _CMU


_LE_ENDING = re.compile(r"[^aeiouy]le$")
_ES_VOICED = re.compile(r"(s|x|z|ch|sh|c|g)es$")
_ED_VOICED = re.compile(r"[td]ed$")
_SPLIT_VOWELS = re.compile(r"(?<![tscgq])io|(?<![tscgq])ia|(?<![qg])ua|iu|[aeiouy]ing$")


def heuristic_count(word: str) -> int:
    """Estimate syllables with spelling rules. Returns 0 for non-alphabetic input."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if not re.search(r"[aeiouy]", w):
        # Looks like an acronym ("pdf", "wtf"): spell it out letter by letter.
        return sum(3 if c == "w" else 1 for c in w)

    base = w
    if len(base) > 2 and base.endswith("es") and not _ES_VOICED.search(base):
        base = base[:-1]  # "makes" -> "make", then the silent-e rule applies
    elif len(base) > 2 and base.endswith("ed") and not _ED_VOICED.search(base):
        base = base[:-2]  # "jumped" -> "jump"
    if len(base) > 2 and base.endswith("e") and not _LE_ENDING.search(base):
        base = base[:-1]  # silent final e

    count = len(re.findall(r"[aeiouy]+", base))
    count += len(_SPLIT_VOWELS.findall(base))
    return max(1, count)


# Contractions in -n't normally add a syllable ("isn't" = 2) except these.
_ONE_SYLLABLE_NT = {"don't", "won't", "can't", "shan't", "ain't", "aren't"}


def _cmu_count(pronunciations: list) -> int:
    return sum(1 for ph in pronunciations[0] if ph[-1].isdigit())


def count_word(word: str) -> int | None:
    """Syllables in a single alphabetic word, or ``None`` if it can't be counted."""
    w = word.lower().replace("’", "'")
    bare = w.replace("'", "")
    if not bare or not re.fullmatch(r"[a-z]+", bare):
        return None
    if "'" in w:
        # Contractions: don't consult OVERRIDES, where "id" means I.D. but "I'd" is one syllable.
        if w.endswith("n't") and w not in _ONE_SYLLABLE_NT:
            base = count_word(w[:-3])
            return None if base is None else base + 1
        cmu = _cmu()
        if cmu is not None and w in cmu:
            return _cmu_count(cmu[w])
        return heuristic_count(bare)
    if bare in OVERRIDES:
        return OVERRIDES[bare]
    cmu = _cmu()
    if cmu is not None and bare in cmu:
        return _cmu_count(cmu[bare])
    return heuristic_count(bare)
