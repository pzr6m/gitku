from gitku.haiku import (
    Token,
    best_non_overlapping,
    deliberate_triples,
    find_windows,
    line_syllables,
    tokenize,
)

BUILD = "the build is broken nobody touched the config and yet here we are"
BUILD_LINES = ("the build is broken", "nobody touched the config", "and yet here we are")


def T(text, syl):
    return Token(text, text.lower().strip(".,"), syl)


def test_tokenize_drops_bullets_and_bare_punctuation():
    assert [t.text for t in tokenize("- the *build* — ok")] == ["the", "build", "ok"]


def test_tokenize_keeps_trailing_punctuation_for_display():
    toks = tokenize("Splash! Silence again.")
    assert [t.text for t in toks] == ["Splash!", "Silence", "again."]
    assert toks[0].ends_sentence and toks[2].ends_sentence


def test_tokenize_marks_uncountable_tokens():
    toks = tokenize("fix v2 parser")
    assert [t.syllables is None for t in toks] == [False, True, False]


def test_tokenize_splits_hyphens_and_underscores():
    toks = tokenize("snake_case well-known")
    assert [t.syllables for t in toks] == [2, 2]


def test_strict_finds_whole_text_haiku():
    windows = find_windows(tokenize(BUILD), strict=True)
    assert [w.lines for w in windows] == [BUILD_LINES]


def test_strict_rejects_wrong_syllable_count():
    assert find_windows(tokenize("fix flaky test that fails on tuesday nights"), strict=True) == []


def test_strict_rejects_trailing_extra_words():
    assert find_windows(tokenize(BUILD + " today"), strict=True) == []


def test_strict_rejects_uncountable_tokens():
    assert find_windows(tokenize("the build is v2 nobody touched the config and yet here we are"), strict=True) == []


def test_loose_finds_haiku_embedded_in_longer_text():
    text = "Note: " + BUILD + ". Moving on to other things now."
    windows = find_windows(tokenize(text), strict=False)
    # the sentence's full stop stays attached to the last word
    assert (*BUILD_LINES[:2], "and yet here we are.") in [w.lines for w in windows]


def _score_of_build_window(text):
    windows = find_windows(tokenize(text), strict=False)
    return max(w.score for w in windows if w.lines[0] == "the build is broken")


def test_loose_scores_mid_sentence_windows_lower_than_clean_ones():
    clean = _score_of_build_window("Hello. " + BUILD + ". Bye.")
    mid = _score_of_build_window("so " + BUILD + " and then more words follow")
    assert clean > mid


def test_dangling_line_endings_are_penalised():
    tokens = [
        T("we", 1), T("fix", 1), T("bugs", 1), T("in", 1), T("the", 1),
        T("old", 1), T("cobwebbed", 2), T("legacy", 3), T("code", 1),
        T("and", 1), T("then", 1), T("we", 1), T("sleep", 1), T("well", 1),
    ]
    (window,) = find_windows(tokens, strict=True)
    assert window.score == 0.6  # 1.0 - 0.3 ("the") - 0.05 - 0.05


def test_clause_punctuation_avoids_the_unpunctuated_penalty():
    tokens = [
        T("we", 1), T("fix", 1), T("bugs", 1), T("daily,", 2),
        T("old", 1), T("cobwebbed", 2), T("legacy", 3), T("code;", 1),
        T("then", 1), T("we", 1), T("sleep", 1), T("well.", 2),
    ]
    (window,) = find_windows(tokens, strict=True)
    assert window.score == 1.0


def test_repetitive_noise_is_not_a_poem():
    assert find_windows(tokenize(" ".join(["go"] * 17)), strict=True) == []


def test_best_non_overlapping_keeps_highest_scores():
    tokens = [T("a", 1)] * 3
    from gitku.haiku import Window

    a = Window(("1", "2", "3"), 0, 10, 0.9)
    b = Window(("4", "5", "6"), 5, 15, 0.95)  # overlaps a, scores higher
    c = Window(("7", "8", "9"), 20, 30, 0.5)
    chosen = best_non_overlapping([a, b, c])
    assert [w.lines[0] for w in chosen] == ["4", "7"]
    assert tokens  # silence unused warning


def test_line_syllables():
    assert line_syllables("the build is broken") == 5
    assert line_syllables("v2 release") is None
    assert line_syllables("") is None


def test_deliberate_triples_detects_layout_haiku():
    lines = ["intro line", "quiet morning light", "settles on the sleeping town", "coffee warms my hands", "outro"]
    assert deliberate_triples(lines) == [
        ("quiet morning light", "settles on the sleeping town", "coffee warms my hands")
    ]


def test_deliberate_triples_ignores_non_haiku():
    assert deliberate_triples(["one two three", "four five six", "seven eight nine"]) == []
