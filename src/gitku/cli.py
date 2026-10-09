"""Command line interface: ``gitku [scan] [PATH]`` and ``gitku laureate [PATH]``."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence

from . import __version__, laureate, render, scan
from .sources import GitError

COMMANDS = ("scan", "laureate")


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("path", nargs="?", default=".", help="repository to scan (default: .)")
    p.add_argument(
        "--sources",
        default=",".join(scan.ALL_SOURCES),
        help="comma-separated: commits,comments,docs (default: all)",
    )
    p.add_argument("--loose", action="store_true",
                   help="also look for haiku hiding inside longer text")
    p.add_argument("--min-score", type=float, default=0.5, metavar="F",
                   help="minimum line-break score 0-1 for accidental haiku (default: 0.5)")
    p.add_argument("--since", metavar="DATE", help="only commits since DATE (anything git accepts)")
    p.add_argument("--max-commits", type=int, default=5000, metavar="N",
                   help="scan at most N commits (default: 5000)")
    p.add_argument("--author", metavar="NAME", help="only poems by authors matching NAME")
    p.add_argument("--only", choices=["accidental", "intentional"],
                   help="show only one kind of haiku")
    p.add_argument("-o", "--output", metavar="FILE", help="write to FILE instead of stdout")
    p.add_argument("--format", choices=["text", "markdown", "json", "svg"], default="text")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")


def build_parser(command: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=f"gitku {command}" if command != "scan" else "gitku",
        description="Find accidental haiku hiding in a git repository.",
    )
    p.add_argument("--version", action="version", version=f"gitku {__version__}")
    _common(p)
    if command == "scan":
        p.add_argument("-n", "--limit", type=int, default=10, metavar="N",
                       help="show the top N haiku, 0 for all (default: 10)")
        p.add_argument("--theme", choices=list(render.THEMES), default="light",
                       help="SVG theme (default: light)")
    return p


def _write(text: str, output: Optional[str]) -> None:
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _use_color(args: argparse.Namespace) -> bool:
    return (
        not args.no_color
        and not args.output
        and "NO_COLOR" not in os.environ
        and sys.stdout.isatty()
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args_list: List[str] = list(sys.argv[1:] if argv is None else argv)
    command = "scan"
    if args_list and args_list[0] in COMMANDS:
        command = args_list.pop(0)
    args = build_parser(command).parse_args(args_list)

    include = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = [s for s in include if s not in scan.ALL_SOURCES]
    if bad or not include:
        print(f"gitku: unknown source(s): {', '.join(bad) or '(none)'}", file=sys.stderr)
        return 2

    try:
        result = scan.collect(
            args.path,
            include=include,
            since=args.since,
            max_commits=args.max_commits or None,
            author=args.author,
            loose=args.loose,
            min_score=args.min_score,
            only=args.only,
        )
    except GitError as exc:
        print(f"gitku: {exc}", file=sys.stderr)
        return 2

    repo_name = os.path.basename(os.path.abspath(args.path)) or args.path

    if command == "laureate":
        rows = laureate.rank(result.poems)
        if args.format == "json":
            _write(laureate.render_json(rows), args.output)
        else:
            _write(laureate.render_text(rows, f"Poet laureate of {repo_name}"), args.output)
        return 0

    poems = result.poems if args.limit == 0 else result.poems[: args.limit]
    summary = dict(
        repo=repo_name,
        commits_scanned=result.commits,
        files_scanned=result.files,
        total_found=len(result.poems),
    )
    if args.format == "json":
        _write(render.render_json(poems, **summary), args.output)
    elif args.format == "markdown":
        _write(render.render_markdown(poems, f"Accidental haiku in {repo_name}"), args.output)
    elif args.format == "svg":
        _write(render.render_svg(poems, f"gitku · {repo_name}", args.theme), args.output)
    else:
        if not poems:
            msg = "No haiku found."
            if not args.loose:
                msg += " Try --loose to search inside longer text."
            _write(msg, args.output)
            return 0
        body = render.render_text(poems, color=_use_color(args))
        acc = sum(1 for p in result.poems if not p.intentional)
        inten = len(result.poems) - acc
        footer = (
            f"{acc} accidental, {inten} intentional haiku "
            f"({result.commits} commits, {result.files} files scanned)"
        )
        if len(poems) < len(result.poems):
            footer += f"; showing {len(poems)}. Use -n 0 for all."
        _write(body + "\n\n" + footer, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
