"""Putting it together: scan a repository and return its poems."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import sources
from .haiku import Window, best_non_overlapping, deliberate_triples, find_windows, tokenize
from .models import Meta, Poem, Unit

ALL_SOURCES = ("commits", "comments", "docs")


@dataclass
class ScanResult:
    poems: List[Poem]
    commits: int = 0
    files: int = 0


def _adjusted(unit: Unit, window: Window) -> float:
    """Commit subjects rarely end in a full stop, but prose in files usually does.
    A file-based poem that stops mid-sentence reads as truncated, so rank it lower."""
    score = window.score
    if unit.meta.kind != "commit" and window.lines[2][-1] not in ".!?…:":
        score -= 0.15
    return round(max(0.0, score), 2)


def poems_from_unit(unit: Unit, loose: bool, min_score: float) -> List[Poem]:
    poems: List[Poem] = []
    for trio in deliberate_triples(unit.lines):
        poems.append(Poem(trio, unit.meta, 1.0, intentional=True))
    for text in unit.strict_texts:
        for w in find_windows(tokenize(text), strict=True):
            score = _adjusted(unit, w)
            if score >= min_score:
                poems.append(Poem(w.lines, unit.meta, score))
    if loose and unit.loose_text:
        windows = [
            replace(w, score=_adjusted(unit, w))
            for w in find_windows(tokenize(unit.loose_text), strict=False)
        ]
        windows = [w for w in windows if w.score >= min_score]
        for w in best_non_overlapping(windows):
            poems.append(Poem(w.lines, unit.meta, w.score))
    return poems


def _key(poem: Poem) -> str:
    return re.sub(r"[^a-z0-9 ]", "", " ".join(poem.lines).lower())


def dedupe(poems: Iterable[Poem]) -> List[Poem]:
    """Keep one poem per distinct text, preferring deliberate and higher-scoring ones."""
    best: Dict[str, Poem] = {}
    for p in poems:
        k = _key(p)
        cur = best.get(k)
        if cur is None or (p.intentional, p.score) > (cur.intentional, cur.score):
            best[k] = p
    return list(best.values())


def attach_blame(repo: str, poems: Sequence[Poem]) -> List[Poem]:
    """Fill in author, commit and date for poems found in files."""
    cache: Dict[Tuple[str, int], Optional[Tuple[str, str, str]]] = {}
    out: List[Poem] = []
    for p in poems:
        if p.meta.blame is None or p.meta.author:
            out.append(p)
            continue
        key = p.meta.blame
        if key not in cache:
            cache[key] = sources.blame_line(repo, key[0], key[1])
        info = cache[key]
        if info:
            author, sha, date = info
            meta = replace(p.meta, author=author, sha=sha, date=date)
        else:
            meta = p.meta
        out.append(replace(p, meta=meta))
    return out


def sort_poems(poems: Iterable[Poem]) -> List[Poem]:
    return sorted(
        poems,
        key=lambda p: (
            p.intentional,
            -p.score,
            p.meta.kind,
            p.meta.location or p.meta.sha or "",
            p.lines,
        ),
    )


def collect(
    repo: str = ".",
    *,
    include: Sequence[str] = ALL_SOURCES,
    since: Optional[str] = None,
    max_commits: Optional[int] = 5000,
    author: Optional[str] = None,
    loose: bool = False,
    min_score: float = 0.5,
    only: Optional[str] = None,
) -> ScanResult:
    sources.ensure_repo(repo)
    found: List[Poem] = []
    stats: Dict[str, int] = {"files": 0}
    commits = 0

    if "commits" in include:
        for unit in sources.iter_commits(repo, since=since, max_commits=max_commits):
            commits += 1
            found.extend(poems_from_unit(unit, loose, min_score))

    want_comments = "comments" in include
    want_docs = "docs" in include
    if want_comments or want_docs:
        for unit in sources.iter_file_units(repo, want_comments, want_docs, stats):
            found.extend(poems_from_unit(unit, loose, min_score))

    poems = attach_blame(repo, dedupe(found))
    if author:
        needle = author.lower()
        poems = [p for p in poems if needle in p.author.lower()]
    if only == "accidental":
        poems = [p for p in poems if not p.intentional]
    elif only == "intentional":
        poems = [p for p in poems if p.intentional]
    return ScanResult(sort_poems(poems), commits=commits, files=stats["files"])
