# Contributing

Thanks for helping make gitku better. Setup:

```bash
pip install -e ".[dev]"
pytest                      # with the CMU dictionary, if installed
GITKU_NO_CMUDICT=1 pytest   # dependency-free syllable counter
```

Both runs must pass.

## Easy ways to help

- **Fix a miscounted word.** Add it to `OVERRIDES` in `src/gitku/syllables.py` (lowercase, no apostrophes) and add a case to `tests/test_syllables.py`.
- **Add a comment style or file type.** See `CODE_EXTS` and `_COMMENT` in `src/gitku/sources.py`.
- **Scan Python docstrings** (not supported yet).
- **Better ranking.** The beauty score lives in `src/gitku/haiku.py` (`_score`) and `src/gitku/scan.py` (`_adjusted`).

## Guidelines

- Keep runtime dependencies at zero; optional extras are fine.
- Tests that need a repository use the `repo` fixture in `tests/conftest.py`, which builds a throwaway repo with fixed authors and dates.
- Please don't add fixtures taken from real projects' commit history.
