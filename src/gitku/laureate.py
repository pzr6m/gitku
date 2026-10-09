"""Ranking the accidental poets of a repository."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .models import Poem


@dataclass
class Laureate:
    author: str
    total: int
    accidental: int
    intentional: int
    avg_score: float
    best: Poem


def rank(poems: Sequence[Poem]) -> List[Laureate]:
    """Group poems by author. Most poems wins; average line-break quality breaks ties."""
    groups: Dict[str, List[Poem]] = {}
    for p in poems:
        groups.setdefault(p.author, []).append(p)
    rows: List[Laureate] = []
    for author, items in groups.items():
        acc = sum(1 for p in items if not p.intentional)
        best = max(items, key=lambda p: (not p.intentional, p.score))
        rows.append(
            Laureate(
                author=author,
                total=len(items),
                accidental=acc,
                intentional=len(items) - acc,
                avg_score=round(sum(p.score for p in items) / len(items), 2),
                best=best,
            )
        )
    rows.sort(key=lambda r: (-r.accidental, -r.total, -r.avg_score, r.author.lower()))
    return rows


def render_text(rows: Sequence[Laureate], title: str = "Poet laureate") -> str:
    if not rows:
        return "No poets found."
    out = [title, ""]
    for i, r in enumerate(rows, 1):
        crown = " ♕" if i == 1 else ""
        out.append(
            f"{i:>2}. {r.author}{crown}  — {r.accidental} accidental"
            + (f", {r.intentional} intentional" if r.intentional else "")
            + f"  (avg beauty {r.avg_score:.2f})"
        )
        out.append("      " + " / ".join(r.best.lines))
    return "\n".join(out)


def render_json(rows: Sequence[Laureate]) -> str:
    payload = [
        {
            "author": r.author,
            "total": r.total,
            "accidental": r.accidental,
            "intentional": r.intentional,
            "avg_score": r.avg_score,
            "best": r.best.to_dict(),
        }
        for r in rows
    ]
    return json.dumps({"laureates": payload}, indent=2, ensure_ascii=False) + "\n"
