"""commit-msg hook: cheer when the message you just wrote happens to be a haiku. Never fails a commit."""

from __future__ import annotations

import sys
from typing import Optional, Sequence

from .models import Meta, Unit
from .render import render_card
from .scan import poems_from_unit
from .sources import clean_message


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return 0
    try:
        with open(args[0], encoding="utf-8", errors="replace") as fh:
            text = "\n".join(l for l in fh.read().splitlines() if not l.startswith("#"))
    except OSError:
        return 0
    lines = clean_message(text)
    if not lines:
        return 0
    strict = [lines[0]] + ([" ".join(lines)] if len(lines) > 1 else [])
    unit = Unit(meta=Meta(kind="commit"), strict_texts=strict, lines=lines, loose_text=" ".join(lines))
    poems = poems_from_unit(unit, loose=False, min_score=0.5)
    if poems:
        print("gitku: that commit message is a haiku!\n")
        print(render_card(poems[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
