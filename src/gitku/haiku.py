"""Finding 5-7-5 haiku inside arbitrary text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .syllables import count_word

PATTERN = (5, 7, 5)

# A line that ends on one of these reads as if it was cut mid-thought.
DANGLING_WORDS = frozenset(
    """the a an of to and or but in on at for with by from as that which this these
    those if then than so my your our their its into onto over under about between
    through""".split()
)

_STRIP_DISPLAY = "`*_~#\"'()[]{}<>"
_STRIP_CORE = ".,;:!?…—–-"
_END_PUNCT = ".,;:!?…"
_SENTENCE_END = ".!?…"


@dataclass(frozen=True)
class Token:
    text: str  # as written, with trailing punctuation
    core: str  # lowercase letters only, for lookups
    syllables: Optional[int]  # None when the token can't be counted

    @property
    def ends_clause(self) -> bool:
        return self.text[-1] in _END_PUNCT

    @property
    def ends_sentence(self) -> bool:
        return self.text[-1] in _SENTENCE_END


def tokenize(text: str) -> List[Token]:
    """Split text into countable tokens, dropping bullets and bare punctuation."""
    tokens: List[Token] = []
    for raw in text.split():
        display = raw.strip(_STRIP_DISPLAY)
        core = display.strip(_STRIP_CORE)
        if not core:
            continue
        parts = [p for p in re.split(r"[-_‐‑]", core) if p]
        total = 0
        counted = True
        for part in parts:
            n = count_word(part)
            if n is None:
                counted = False
                break
            total += n
        letters = re.sub(r"[^a-z]", "", core.lower())
        tokens.append(Token(display, letters, total if counted else None))
    return tokens


def _score(tokens: Sequence[Token], start: int, cuts: Sequence[int], strict: bool) -> float:
    """Rate how natural the line breaks are, from 0 to 1."""
    score = 1.0
    for cut in cuts:
        last = tokens[cut - 1]
        if last.core in DANGLING_WORDS:
            score -= 0.3
        elif not last.ends_clause:
            score -= 0.05
    if not strict:
        # A window plucked from the middle of a sentence should at least
        # start and end on a sentence or clause boundary.
        if start > 0 and not tokens[start - 1].ends_clause:
            score -= 0.2
        end = cuts[-1]
        if end < len(tokens) and not tokens[end - 1].ends_clause:
            score -= 0.2
    return max(0.0, round(score, 2))


def _plausible(window: Sequence[Token]) -> bool:
    """Reject windows that are mostly noise (repeated words, walls of acronyms)."""
    words = [t.core for t in window]
    if len(words) < 5:
        return False
    if len(set(words)) < max(3, len(words) // 2):
        return False
    return True


@dataclass(frozen=True)
class Window:
    lines: Tuple[str, str, str]
    start: int
    end: int
    score: float


def find_windows(tokens: Sequence[Token], strict: bool = True) -> List[Window]:
    """Find 5-7-5 windows.

    With ``strict`` the whole token list must be the haiku. Otherwise every
    starting position is tried.
    """
    n = len(tokens)
    found: List[Window] = []
    starts = [0] if strict else range(n)
    for i in starts:
        j = i
        cuts: List[int] = []
        ok = True
        for target in PATTERN:
            total = 0
            while j < n and total < target:
                s = tokens[j].syllables
                if s is None:
                    ok = False
                    break
                total += s
                j += 1
            if not ok or total != target:
                ok = False
                break
            cuts.append(j)
        if not ok or (strict and j != n):
            continue
        window = tokens[i:j]
        if not _plausible(window):
            continue
        a, b, c = cuts
        lines = (
            " ".join(t.text for t in tokens[i:a]),
            " ".join(t.text for t in tokens[a:b]),
            " ".join(t.text for t in tokens[b:c]),
        )
        found.append(Window(lines, i, j, _score(tokens, i, cuts, strict)))
    return found


def best_non_overlapping(windows: Sequence[Window]) -> List[Window]:
    """Greedily keep the highest-scoring windows that don't share tokens."""
    chosen: List[Window] = []
    for w in sorted(windows, key=lambda w: (-w.score, w.start)):
        if all(w.end <= c.start or w.start >= c.end for c in chosen):
            chosen.append(w)
    return sorted(chosen, key=lambda w: w.start)


def line_syllables(line: str) -> Optional[int]:
    """Total syllables on one line, or ``None`` if any word can't be counted."""
    total = 0
    toks = tokenize(line)
    if not toks:
        return None
    for t in toks:
        if t.syllables is None:
            return None
        total += t.syllables
    return total


def deliberate_triples(lines: Sequence[str]) -> List[Tuple[str, str, str]]:
    """Consecutive line triples that are laid out as a 5-7-5 haiku on purpose."""
    cleaned = [l.strip() for l in lines if l.strip()]
    out: List[Tuple[str, str, str]] = []
    counts = [line_syllables(l) for l in cleaned]
    for i in range(len(cleaned) - 2):
        if (counts[i], counts[i + 1], counts[i + 2]) == PATTERN:
            out.append((cleaned[i], cleaned[i + 1], cleaned[i + 2]))
    return out
