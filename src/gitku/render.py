"""Turning poems into text cards, Markdown, JSON and SVG."""

from __future__ import annotations

import json
import re
from typing import List, Sequence
from xml.sax.saxutils import escape

from .models import Poem

SOURCE_LABELS = {"commit": "commit", "comment": "code comment", "doc": "docs"}


def attribution(poem: Poem) -> str:
    """One-line credit: author, commit, date, where it was found."""
    m = poem.meta
    parts = [m.author or "unknown author"]
    if m.sha:
        parts.append(m.sha)
    if m.date:
        parts.append(m.date)
    where = SOURCE_LABELS.get(m.kind, m.kind)
    if m.location:
        where += f" at {m.location}"
    parts.append(where)
    if poem.intentional:
        parts.append("intentional")
    return " · ".join(parts)


# --------------------------------------------------------------------------
# terminal
# --------------------------------------------------------------------------


def render_card(poem: Poem, color: bool = False) -> str:
    inner = max(len(l) for l in poem.lines)
    top = "╭" + "─" * (inner + 4) + "╮"
    bottom = "╰" + "─" * (inner + 4) + "╯"
    rows = [f"│  {l.ljust(inner)}  │" for l in poem.lines]
    credit = "— " + attribution(poem)
    if color:
        credit = f"\x1b[2m{credit}\x1b[0m"
    return "\n".join([top, *rows, bottom, "  " + credit])


def render_text(poems: Sequence[Poem], color: bool = False) -> str:
    return "\n\n".join(render_card(p, color) for p in poems)


# --------------------------------------------------------------------------
# markdown / json
# --------------------------------------------------------------------------


def render_markdown(poems: Sequence[Poem], title: str = "Accidental haiku") -> str:
    out: List[str] = [f"# {title}", ""]
    for p in poems:
        out.extend(f"> {line}  " for line in p.lines)
        out.append(">")
        out.append(f"> — *{attribution(p)}*")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_json(poems: Sequence[Poem], **summary: object) -> str:
    payload = {**summary, "poems": [p.to_dict() for p in poems]}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# svg
# --------------------------------------------------------------------------

THEMES = {
    "light": dict(bg="#efe9dc", card="#faf6ee", border="#d8cfbb", text="#2b2a27",
                  muted="#857d6a", accent="#b4523a"),
    "dark": dict(bg="#101216", card="#1a1d23", border="#2a2e37", text="#ebe8e2",
                 muted="#8b909a", accent="#e08a6d"),
}

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _esc(s: str) -> str:
    return escape(_CONTROL.sub("", s))


def render_svg(poems: Sequence[Poem], title: str = "gitku", theme: str = "light") -> str:
    t = THEMES.get(theme, THEMES["light"])
    pad, gap, line_h = 24, 18, 34
    char_w, mono_w = 11.8, 7.4
    shown = list(poems)

    longest_line = max((len(l) for p in shown for l in p.lines), default=24)
    longest_credit = max((len(attribution(p)) for p in shown), default=0)
    card_w = max(560, int(longest_line * char_w) + 96, int(longest_credit * mono_w) + 64)
    width = card_w + 2 * pad
    card_h = 30 + 3 * line_h + 56
    header_h = 64

    body: List[str] = []
    y = header_h
    if not shown:
        body.append(
            f'<text x="{pad}" y="{y + 30}" font-family="Georgia, serif" font-size="20" '
            f'fill="{t["muted"]}">No haiku found.</text>'
        )
        y += 60
    for p in shown:
        body.append(
            f'<rect x="{pad}" y="{y}" width="{card_w}" height="{card_h}" rx="12" '
            f'fill="{t["card"]}" stroke="{t["border"]}"/>'
        )
        ty = y + 52
        for line in p.lines:
            body.append(
                f'<text x="{pad + 32}" y="{ty}" font-family="Georgia, \'Times New Roman\', serif" '
                f'font-size="22" fill="{t["text"]}">{_esc(line)}</text>'
            )
            ty += line_h
        body.append(
            f'<text x="{pad + 32}" y="{y + card_h - 20}" '
            f'font-family="ui-monospace, Menlo, Consolas, monospace" font-size="12" '
            f'fill="{t["muted"]}">— {_esc(attribution(p))}</text>'
        )
        y += card_h + gap

    height = y + pad - gap
    head = (
        f'<text x="{pad}" y="42" font-family="Georgia, serif" font-size="26" '
        f'font-weight="bold" fill="{t["accent"]}">{_esc(title)}</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}">\n'
        f"<title>{_esc(title)}</title>\n"
        f'<rect width="100%" height="100%" fill="{t["bg"]}"/>\n'
        f"{head}\n" + "\n".join(body) + "\n</svg>\n"
    )
