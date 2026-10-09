import pytest

from gitku import laureate, scan
from gitku.sources import GitError, clean_message

BUILD = "the build is broken / nobody touched the config / and yet here we are"
CACHE_GONE = "the old cache is gone / we cleared it out of our disks / space returns to us"
RETRY = "stop the retry loop / before it eats the whole queue / or we all lose sleep"
MORNING = "quiet morning light / settles on the sleeping town / coffee warms my hands"
CACHE_LIE = "never trust the cache / it lies to you when you least / expect it again"


def by_text(result):
    return {" / ".join(p.lines): p for p in result.poems}


def test_finds_every_kind_of_poem(demo_repo):
    found = by_text(scan.collect(str(demo_repo.path)))
    assert set(found) == {BUILD, CACHE_GONE, RETRY, MORNING, CACHE_LIE}


def test_commit_poem_attribution(demo_repo):
    p = by_text(scan.collect(str(demo_repo.path)))[BUILD]
    assert (p.author, p.meta.date, p.meta.kind) == ("Ada Lovelace", "2025-03-04", "commit")
    assert len(p.meta.sha) == 7
    assert not p.intentional


def test_intentional_layout_is_flagged_and_not_duplicated(demo_repo):
    result = scan.collect(str(demo_repo.path))
    cache_gone = [p for p in result.poems if " / ".join(p.lines) == CACHE_GONE]
    assert len(cache_gone) == 1
    assert cache_gone[0].intentional


def test_trailers_do_not_break_commit_poems(demo_repo):
    assert RETRY in by_text(scan.collect(str(demo_repo.path)))


def test_file_poems_are_attributed_via_blame(demo_repo):
    found = by_text(scan.collect(str(demo_repo.path)))
    for text, where in [(MORNING, "README.md:3"), (CACHE_LIE, "util.py:4")]:
        p = found[text]
        assert p.author == "Grace Hopper"
        assert p.meta.date == "2025-03-08"
        assert p.meta.location == where


def test_comment_poems_are_accidental_and_doc_layout_is_intentional(demo_repo):
    found = by_text(scan.collect(str(demo_repo.path)))
    assert found[MORNING].intentional
    assert not found[CACHE_LIE].intentional


def test_only_filter(demo_repo):
    acc = scan.collect(str(demo_repo.path), only="accidental")
    assert all(not p.intentional for p in acc.poems)
    inten = scan.collect(str(demo_repo.path), only="intentional")
    assert {" / ".join(p.lines) for p in inten.poems} == {CACHE_GONE, MORNING}


def test_sources_filter(demo_repo):
    commits = scan.collect(str(demo_repo.path), include=["commits"])
    assert {p.meta.kind for p in commits.poems} == {"commit"}
    assert commits.files == 0
    files = scan.collect(str(demo_repo.path), include=["docs", "comments"])
    assert {p.meta.kind for p in files.poems} == {"doc", "comment"}
    assert files.commits == 0


def test_author_filter(demo_repo):
    result = scan.collect(str(demo_repo.path), author="grace")
    assert {p.author for p in result.poems} == {"Grace Hopper"}


def test_max_commits_limits_history(demo_repo):
    result = scan.collect(str(demo_repo.path), include=["commits"], max_commits=1)
    assert result.commits == 1
    assert result.poems == []  # the newest commit is "add docs and a helper"


def test_since_filters_old_commits(demo_repo):
    result = scan.collect(str(demo_repo.path), include=["commits"], since="2099-01-01")
    assert result.commits == 0


def test_untracked_files_are_ignored(demo_repo):
    (demo_repo.path / "NOTES.md").write_text("never trust the cache\nit lies to you when you least\nexpect it\n")
    result = scan.collect(str(demo_repo.path), include=["docs"])
    assert all(p.meta.location != "NOTES.md:1" for p in result.poems)


def test_loose_mode_finds_hidden_haiku(repo):
    repo.commit(
        "refactor: tidy things\n\n"
        "Note: the build is broken nobody touched the config and yet here we are. "
        "More details follow in the ticket."
    )
    strict = scan.collect(str(repo.path))
    loose = scan.collect(str(repo.path), loose=True)
    assert strict.poems == []
    assert BUILD + "." in by_text(loose)  # the sentence's full stop stays on the last line


def test_scan_rejects_non_repositories(tmp_path):
    with pytest.raises(GitError):
        scan.collect(str(tmp_path))


def test_empty_repository_is_fine(repo):
    assert scan.collect(str(repo.path)).poems == []


def test_file_poems_cut_off_mid_sentence_rank_lower_than_commits():
    from gitku.haiku import Window
    from gitku.models import Meta, Unit

    window = Window(("a b c d e", "a b c d e f g", "a b c d e"), 0, 17, 0.85)
    commit = Unit(meta=Meta(kind="commit"))
    comment = Unit(meta=Meta(kind="comment"))
    assert scan._adjusted(commit, window) == 0.85
    assert scan._adjusted(comment, window) == 0.7
    ended = Window(("a b c d e", "a b c d e f g", "a b c d e."), 0, 17, 0.85)
    assert scan._adjusted(comment, ended) == 0.85


def test_clean_message_strips_trailers_urls_and_type_prefix():
    msg = (
        "feat(parser): handle empty input\n\n"
        "details here\n"
        "https://example.com/issue/1\n"
        "Signed-off-by: A <a@b.c>\n"
        "Co-Authored-By: B <b@c.d>\n"
    )
    assert clean_message(msg) == ["handle empty input", "details here"]


def test_laureate_ranks_by_accidental_poems(demo_repo):
    rows = laureate.rank(scan.collect(str(demo_repo.path)).poems)
    top = rows[0]
    assert top.author in {"Ada Lovelace", "Linus Example", "Grace Hopper"}
    by_author = {r.author: r for r in rows}
    assert by_author["Ada Lovelace"].accidental == 1
    assert by_author["Ada Lovelace"].intentional == 1
    assert by_author["Grace Hopper"].accidental == 1
    assert by_author["Linus Example"].accidental == 1
    assert sum(r.total for r in rows) == 5
