"""Reading text out of a git repository: commits, code comments and docs."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Dict, Iterator, List, Optional, Tuple

from .models import Meta, Unit


class GitError(RuntimeError):
    """Raised when git is missing or a command fails."""


def run_git(repo: str, *args: str, check: bool = True) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise GitError("the 'git' executable was not found on PATH") from None
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def ensure_repo(repo: str) -> None:
    out = run_git(repo, "rev-parse", "--is-inside-work-tree", check=False).strip()
    if out != "true":
        raise GitError(f"{repo!r} is not inside a git repository")


# --------------------------------------------------------------------------
# commits
# --------------------------------------------------------------------------

_TRAILER = re.compile(
    r"^(?:signed-off-by|co-authored-by|reviewed-by|acked-by|tested-by|reported-by|"
    r"cc|change-id|claude-session|fixes|closes|refs|see-also)\s*:.*$",
    re.IGNORECASE,
)
_URL_LINE = re.compile(r"^(?:https?://|git@)\S+$")
_CONVENTIONAL_PREFIX = re.compile(r"^\w+(?:\([^)]*\))?!?:\s+")


def clean_message(message: str) -> List[str]:
    """Non-blank lines of a commit message, minus trailers, URLs and type prefixes."""
    lines: List[str] = []
    for raw in message.splitlines():
        line = raw.strip()
        if not line or _TRAILER.match(line) or _URL_LINE.match(line):
            continue
        lines.append(line)
    if lines:
        lines[0] = _CONVENTIONAL_PREFIX.sub("", lines[0])
    return [l for l in lines if l]


def iter_commits(
    repo: str, since: Optional[str] = None, max_commits: Optional[int] = None
) -> Iterator[Unit]:
    args = ["log", "--no-merges", "--format=%x1e%H%x1f%an%x1f%aI%x1f%B"]
    if since:
        args.append(f"--since={since}")
    if max_commits:
        args.append(f"-n{max_commits}")
    out = run_git(repo, *args, check=False)
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        parts = record.split("\x1f", 3)
        if len(parts) < 4:
            continue
        sha, author, date, body = parts
        lines = clean_message(body)
        if not lines:
            continue
        meta = Meta(kind="commit", author=author, sha=sha[:7], date=date[:10])
        strict = [lines[0]]
        full = " ".join(lines)
        if len(lines) > 1:
            strict.append(full)
        yield Unit(meta=meta, strict_texts=strict, lines=lines, loose_text=full)


# --------------------------------------------------------------------------
# files
# --------------------------------------------------------------------------

CODE_EXTS = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".h",
    ".cc", ".cpp", ".hpp", ".java", ".kt", ".swift", ".rb", ".sh", ".bash", ".zsh",
    ".php", ".cs", ".lua", ".sql", ".hs", ".ex", ".exs", ".scala", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".dart", ".r", ".pl", ".vue", ".svelte", ".css", ".scss",
}
CODE_NAMES = {"Dockerfile", "Makefile", "Rakefile", "Gemfile"}
DOC_EXTS = {".md", ".markdown", ".rst", ".txt", ".adoc"}
SKIP_FRAGMENTS = ("node_modules/", "vendor/", "third_party/", "/dist/", ".min.", "/build/")
MAX_BYTES = 512 * 1024

_COMMENT = re.compile(
    r"^\s*(?:#\s+|//+\s?|--\s+|;+\s+|\*\s+|/\*+\s?|<!--\s?)(.*?)\s*(?:\*/|-->)?\s*$"
)
_LIST_MARKER = re.compile(r"^(?:[-*+>]\s+|\d+[.)]\s+|#{1,6}\s+)")
_RULE = re.compile(r"^[=\-~`_*]{3,}$")


def tracked_files(repo: str) -> List[str]:
    out = run_git(repo, "ls-files", "-z")
    return [p for p in out.split("\0") if p]


def _file_kind(path: str) -> Optional[str]:
    if any(frag in "/" + path for frag in SKIP_FRAGMENTS):
        return None
    pp = PurePosixPath(path)
    if pp.suffix.lower() in DOC_EXTS:
        return "doc"
    if pp.suffix.lower() in CODE_EXTS or pp.name in CODE_NAMES:
        return "comment"
    return None


def comment_units(path: str, text: str) -> Iterator[Unit]:
    """Blocks of consecutive comment lines."""
    block: List[Tuple[int, str]] = []
    blocks: List[List[Tuple[int, str]]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        m = _COMMENT.match(line)
        if m and m.group(1):
            block.append((lineno, m.group(1)))
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    for blk in blocks:
        lines = [t for _, t in blk]
        first = blk[0][0]
        strict = list(dict.fromkeys(lines))
        joined = " ".join(lines)
        if len(lines) > 1:
            strict.append(joined)
        meta = Meta(kind="comment", location=f"{path}:{first}", blame=(path, first))
        yield Unit(meta=meta, strict_texts=strict, lines=lines, loose_text=joined)


def doc_units(path: str, text: str) -> Iterator[Unit]:
    """Paragraphs of prose, skipping code fences, tables and rules."""
    paras: List[List[Tuple[int, str]]] = []
    para: List[Tuple[int, str]] = []
    in_fence = False

    def flush() -> None:
        nonlocal para
        if para:
            paras.append(para)
            para = []

    for lineno, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            flush()
            continue
        if in_fence:
            continue
        s = _LIST_MARKER.sub("", s)
        if not s or _RULE.match(s) or s.startswith(("|", "<", "![")):
            flush()
            continue
        para.append((lineno, s))
    flush()
    for p in paras:
        lines = [t for _, t in p]
        first = p[0][0]
        strict = list(dict.fromkeys(lines))
        joined = " ".join(lines)
        if len(lines) > 1:
            strict.append(joined)
        meta = Meta(kind="doc", location=f"{path}:{first}", blame=(path, first))
        yield Unit(meta=meta, strict_texts=strict, lines=lines, loose_text=joined)


def iter_file_units(
    repo: str, comments: bool, docs: bool, stats: Dict[str, int]
) -> Iterator[Unit]:
    from pathlib import Path

    root = Path(repo)
    for path in tracked_files(repo):
        kind = _file_kind(path)
        if kind is None or (kind == "comment" and not comments) or (kind == "doc" and not docs):
            continue
        fp = root / path
        try:
            if not fp.is_file() or fp.stat().st_size > MAX_BYTES:
                continue
            text = fp.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        stats["files"] = stats.get("files", 0) + 1
        gen = comment_units(path, text) if kind == "comment" else doc_units(path, text)
        yield from gen


# --------------------------------------------------------------------------
# blame
# --------------------------------------------------------------------------


def blame_line(repo: str, path: str, line: int) -> Optional[Tuple[str, str, str]]:
    """(author, short sha, date) for one line, or ``None`` if not committed yet."""
    out = run_git(repo, "blame", "--porcelain", "-L", f"{line},{line}", "--", path, check=False)
    if not out:
        return None
    first = out.splitlines()[0].split()
    if not first:
        return None
    sha = first[0]
    if set(sha) == {"0"}:
        return None
    author = ""
    when = ""
    for row in out.splitlines():
        if row.startswith("author "):
            author = row[len("author "):]
        elif row.startswith("author-time "):
            try:
                ts = int(row.split()[1])
                when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            except ValueError:
                when = ""
    return author, sha[:7], when
