import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest


class Repo:
    """A throwaway git repository with controllable authors and dates."""

    def __init__(self, path: Path):
        self.path = path
        self._git("init", "-q", "-b", "main")

    def _env(self, author: str, date: str) -> Dict[str, str]:
        env = dict(os.environ)
        env.update(
            GIT_AUTHOR_NAME=author,
            GIT_AUTHOR_EMAIL=f"{author.split()[0].lower()}@example.com",
            GIT_COMMITTER_NAME=author,
            GIT_COMMITTER_EMAIL=f"{author.split()[0].lower()}@example.com",
            GIT_AUTHOR_DATE=f"{date}T12:00:00+00:00",
            GIT_COMMITTER_DATE=f"{date}T12:00:00+00:00",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_SYSTEM=os.devnull,
        )
        return env

    def _git(self, *args: str, author: str = "Test", date: str = "2025-01-01", stdin: Optional[str] = None):
        return subprocess.run(
            ["git", "-c", "commit.gpgsign=false", *args],
            cwd=self.path,
            env=self._env(author, date),
            input=stdin,
            text=True,
            capture_output=True,
            check=True,
        )

    def commit(
        self,
        message: str,
        files: Optional[Dict[str, str]] = None,
        author: str = "Ada Lovelace",
        date: str = "2025-03-04",
    ) -> None:
        for name, content in (files or {}).items():
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self._git("add", name)
        self._git("commit", "--allow-empty", "-q", "-F", "-", author=author, date=date, stdin=message)


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    return Repo(tmp_path)


@pytest.fixture
def demo_repo(repo: Repo) -> Repo:
    """A small repo containing every kind of poem gitku can find."""
    repo.commit("the build is broken nobody touched the config and yet here we are",
                author="Ada Lovelace", date="2025-03-04")
    repo.commit("the old cache is gone\nwe cleared it out of our disks\nspace returns to us",
                author="Ada Lovelace", date="2025-03-05")
    repo.commit(
        "stop the retry loop before it eats the whole queue or we all lose sleep\n\n"
        "Co-Authored-By: Someone Else <else@example.com>",
        author="Linus Example", date="2025-03-06",
    )
    repo.commit("update dependencies", author="Linus Example", date="2025-03-07")
    repo.commit(
        "add docs and a helper",
        files={
            "README.md": "# Demo\n\nquiet morning light\nsettles on the sleeping town\ncoffee warms my hands\n",
            "util.py": "def f():\n    return 1\n\n# never trust the cache it lies to you when you least expect it again\n",
        },
        author="Grace Hopper", date="2025-03-08",
    )
    return repo
