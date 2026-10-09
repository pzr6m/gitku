#!/usr/bin/env python3
"""Copy the syllable OVERRIDES from src/gitku/syllables.py into docs/gitku.js.

Run after editing OVERRIDES so the website keeps counting like the CLI:

    python scripts/sync_overrides.py          # rewrite docs/gitku.js
    python scripts/sync_overrides.py --check  # exit 1 if out of date (used in CI)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from gitku.syllables import OVERRIDES  # noqa: E402

JS = ROOT / "docs" / "gitku.js"
BLOCK = re.compile(r"(// <overrides>[^\n]*\n)(.*?)(\n  // </overrides>)", re.DOTALL)


def render() -> str:
    body = json.dumps(dict(sorted(OVERRIDES.items())), separators=(",", ":"))
    return f"  const OVERRIDES = {body};"


def main() -> int:
    text = JS.read_text(encoding="utf-8")
    new = BLOCK.sub(lambda m: m.group(1) + render() + m.group(3), text)
    if "--check" in sys.argv:
        if new != text:
            print("docs/gitku.js is out of date; run: python scripts/sync_overrides.py")
            return 1
        return 0
    JS.write_text(new, encoding="utf-8")
    print(f"wrote {len(OVERRIDES)} overrides to {JS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
