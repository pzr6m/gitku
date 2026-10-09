import json
import xml.etree.ElementTree as ET

import pytest

from gitku import laureate, render, scan
from gitku.cli import main
from gitku.models import Meta, Poem


def poem(author="Ada Lovelace", kind="commit", intentional=False):
    return Poem(
        ("the build is broken", "nobody touched the config", "and yet here we are"),
        Meta(kind=kind, author=author, sha="abc1234", date="2025-03-04"),
        0.85,
        intentional,
    )


def test_card_has_box_three_lines_and_credit():
    out = render.render_card(poem())
    lines = out.splitlines()
    assert lines[0].startswith("╭") and lines[4].startswith("╰")
    assert "nobody touched the config" in lines[2]
    assert "Ada Lovelace" in lines[5] and "abc1234" in lines[5]
    assert len({len(l) for l in lines[:5]}) == 1  # box edges line up


def test_card_color_only_on_request():
    assert "\x1b[" not in render.render_card(poem())
    assert "\x1b[" in render.render_card(poem(), color=True)


def test_attribution_mentions_location_and_intent():
    p = Poem(poem().lines, Meta(kind="doc", author="G", location="README.md:3"), 1.0, True)
    text = render.attribution(p)
    assert "docs at README.md:3" in text and "intentional" in text


def test_markdown_blockquote():
    md = render.render_markdown([poem()], "Title")
    assert md.startswith("# Title")
    assert "> the build is broken  " in md and "— *Ada Lovelace" in md


def test_json_roundtrip():
    data = json.loads(render.render_json([poem()], repo="demo"))
    assert data["repo"] == "demo"
    assert data["poems"][0]["lines"][0] == "the build is broken"
    assert data["poems"][0]["source"] == "commit"
    assert "blame" not in data["poems"][0]


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_svg_is_valid_xml(theme):
    svg = render.render_svg([poem(), poem(kind="doc")], "demo", theme)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert svg.count("<rect") == 3  # background + two cards


def test_svg_escapes_markup_in_text():
    svg = render.render_svg([poem(author="A & <B>")])
    ET.fromstring(svg)
    assert "A &amp; &lt;B&gt;" in svg


def test_svg_with_no_poems_is_still_valid():
    ET.fromstring(render.render_svg([]))


def test_laureate_text_and_json():
    rows = laureate.rank([poem(), poem("Grace"), poem("Grace", intentional=True)])
    text = laureate.render_text(rows, "Poet laureate of demo")
    assert text.splitlines()[0] == "Poet laureate of demo"
    assert "Grace" in text and "Ada Lovelace" in text
    assert json.loads(laureate.render_json(rows))["laureates"][0]["author"] in {"Ada Lovelace", "Grace"}


# ---- command line -------------------------------------------------------


def test_cli_default_scan(demo_repo, capsys):
    assert main([str(demo_repo.path)]) == 0
    out = capsys.readouterr().out
    assert "the build is broken" in out
    assert "accidental" in out and "commits" in out


def test_cli_limit_and_footer(demo_repo, capsys):
    assert main([str(demo_repo.path), "-n", "1"]) == 0
    out = capsys.readouterr().out
    assert out.count("╭") == 1
    assert "showing 1" in out


def test_cli_json(demo_repo, capsys):
    assert main([str(demo_repo.path), "--format", "json", "-n", "0"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total_found"] == len(data["poems"]) == 5
    assert data["commits_scanned"] == 5


def test_cli_writes_svg_file(demo_repo, tmp_path):
    out = tmp_path / "poems.svg"
    assert main([str(demo_repo.path), "--format", "svg", "--theme", "dark", "-o", str(out)]) == 0
    ET.fromstring(out.read_text(encoding="utf-8"))


def test_cli_markdown(demo_repo, capsys):
    assert main([str(demo_repo.path), "--format", "markdown"]) == 0
    assert capsys.readouterr().out.startswith("# Accidental haiku in")


def test_cli_laureate(demo_repo, capsys):
    assert main(["laureate", str(demo_repo.path)]) == 0
    out = capsys.readouterr().out
    assert "Poet laureate of" in out and "Grace Hopper" in out


def test_cli_no_results_hint(repo, capsys):
    repo.commit("update dependencies")
    assert main([str(repo.path)]) == 0
    assert "--loose" in capsys.readouterr().out


def test_cli_rejects_unknown_source(demo_repo, capsys):
    assert main([str(demo_repo.path), "--sources", "commits,bogus"]) == 2
    assert "bogus" in capsys.readouterr().err


def test_cli_not_a_repo(tmp_path, capsys):
    assert main([str(tmp_path)]) == 2
    assert "not inside a git repository" in capsys.readouterr().err


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "gitku 0.1.0" in capsys.readouterr().out
