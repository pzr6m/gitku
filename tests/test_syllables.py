import pytest

from gitku.syllables import OVERRIDES, count_word, heuristic_count


@pytest.mark.parametrize(
    "word,expected",
    [
        ("build", 1), ("broken", 2), ("nobody", 3), ("touched", 1), ("table", 2),
        ("file", 1), ("little", 2), ("example", 3), ("makes", 1), ("jumped", 1),
        ("wanted", 2), ("tried", 1), ("playing", 2), ("flying", 2), ("doing", 2),
        ("timeout", 2), ("actual", 3), ("silence", 2), ("again", 2), ("the", 1),
        ("be", 1), ("are", 1), ("hello", 2), ("world", 1),
    ],
)
def test_heuristic_common_words(word, expected):
    assert heuristic_count(word) == expected


def test_heuristic_spells_out_acronyms():
    assert heuristic_count("pdf") == 3
    assert heuristic_count("wtf") == 5  # "w" is three syllables
    assert heuristic_count("pr") == 2


def test_heuristic_non_alphabetic_is_zero():
    assert heuristic_count("123") == 0
    assert heuristic_count("") == 0


@pytest.mark.parametrize(
    "word,expected",
    [("api", 3), ("config", 2), ("https", 5), ("json", 2), ("repo", 2), ("git", 1), ("refactoring", 4)],
)
def test_developer_jargon_overrides(word, expected):
    assert count_word(word) == expected


def test_overrides_are_case_insensitive():
    assert count_word("API") == 3
    assert count_word("Config") == 2


def test_contractions():
    assert count_word("don't") == 1
    assert count_word("can't") == 1
    assert count_word("isn’t") == 2
    assert count_word("doesn't") == 2
    assert count_word("it's") == 1
    assert count_word("I'd") == 1  # not "id" (I.D.)


@pytest.mark.parametrize("token", ["v2", "foo.py", "", "a/b", "x86", "100%"])
def test_uncountable_tokens_return_none(token):
    assert count_word(token) is None


def test_overrides_are_sane():
    assert all(isinstance(v, int) and v >= 1 for v in OVERRIDES.values())
    assert all(k == k.lower() for k in OVERRIDES)
