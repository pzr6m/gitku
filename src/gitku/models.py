"""Plain data containers shared across gitku."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Meta:
    """Where a piece of text came from."""

    kind: str  # "commit", "comment" or "doc"
    author: Optional[str] = None
    sha: Optional[str] = None
    date: Optional[str] = None  # ISO date, YYYY-MM-DD
    location: Optional[str] = None  # "path:line" for files
    blame: Optional[Tuple[str, int]] = None  # (path, line) still to be resolved


@dataclass
class Unit:
    """A chunk of text that might contain a haiku.

    ``strict_texts`` are strings that must be a haiku in their entirety.
    ``lines`` are the original lines, used to spot deliberate 5-7-5 layouts.
    ``loose_text`` is the full text, searched for haiku hiding inside it.
    """

    meta: Meta
    strict_texts: List[str] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    loose_text: str = ""


@dataclass(frozen=True)
class Poem:
    lines: Tuple[str, str, str]
    meta: Meta
    score: float
    intentional: bool = False

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def author(self) -> str:
        return self.meta.author or "unknown"

    def to_dict(self) -> dict:
        d = asdict(self.meta)
        d.pop("blame", None)
        return {
            "lines": list(self.lines),
            "score": self.score,
            "intentional": self.intentional,
            "source": d.pop("kind"),
            **d,
        }
