# Demo project: `./demo/`

## Purpose

`nepkit`'s README and DEMO.md document the library and CLI, but there is
nowhere a newcomer can run small, focused, narrated examples of the library's
public API. `./demo/` fills that gap: a set of standalone Python scripts, one
per use case, meant to be read top-to-bottom and run individually.

Audience: people learning/evaluating the library (not contributors, not a
personal sandbox, not a README-linked showcase). Scripts should read like a
guided tour with comments explaining *why*, not just what.

## Non-goals

- Not a packaged example app (no CLI wrapper, no web app, no notebook).
- Not a test suite — no `assert`, no pytest, no CI wiring. Verification is
  "run it and read the output," done once during implementation.
- Not part of the shipped `nepkit` distribution — excluded from `mypy`'s
  strict `files` list; not added to `pyproject.toml` dependencies.
- Does not extend or duplicate DEMO.md (which documents the *CLI*); this is
  library-only, `import nepkit` usage.

## Structure

```
demo/
├── README.md                     # what this is, how to run, script index
├── _bootstrap.py                 # sys.path shim, imported first by every script
├── 01_basic_conversion.py
├── 02_parsing_and_formatting.py
├── 03_error_handling.py
└── 04_datetime_conversion.py
```

No `__init__.py` — these are standalone scripts, not a package.

## Import mechanism

Per the user's explicit choice: no packaging, no local path dependency. Each
script begins:

```python
import _bootstrap  # noqa: F401 -- inserts ../src onto sys.path as a side effect
```

`_bootstrap.py`:

```python
"""Make the in-repo nepkit importable without installing it."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
```

This works identically whether invoked as `python demo/01_basic_conversion.py`
from the repo root or `python 01_basic_conversion.py` from inside `demo/`,
because Python always puts the executed script's own directory at
`sys.path[0]`. Every script always runs against the local `src/` tree, never
an installed copy.

## Script contents

Each script is self-contained, runs top-to-bottom with no CLI args, and
prints its results with a short comment above each call explaining the point
being made. Exact API surface used, verified against `src/nepkit/`:

**01_basic_conversion.py**
- `BSDate(year, month, day)` construction and validation
- `bs_to_ad(BSDate) -> date`, `ad_to_bs(date) -> BSDate` round trip
- `days_in_month(year, month)` showing two different lengths (e.g. 32 vs 29)
  to make the point that BS months aren't fixed-length
- `MIN_BS_YEAR`, `MAX_BS_YEAR` — the supported range

**02_parsing_and_formatting.py**
- `parse_bs_date`: ISO form and named form (incl. a romanisation variant like
  `"Baishakh"`)
- `parse_ad_date`: ISO form and named form (`"30 Jul 2024"`)
- `format_bs_date` / `format_ad_date`: default, `named=True`,
  `named=True, devnagari=True`
- `to_devnagari_numerals`, `bs_month_name`, `weekday_name`
- `BSDate.fromisoformat`, `str(BSDate(...))`
- A comment (no code) calling out that `BSDate.isoformat()`'s output is not a
  real ISO 8601 date and must not be passed to `datetime.date.fromisoformat`

**03_error_handling.py**
- Trigger and catch `InvalidDateError` (bad month, e.g. month 13; bad day,
  e.g. day 33 in a 32-day month)
- Trigger and catch `DateOutOfRangeError` (a real BS date outside
  2000-01-01..2090-12-30, e.g. year 2095)
- Show catching the narrow types separately vs. catching the shared
  `DateError` base when the caller only needs "this input didn't work"
- Print the hierarchy (`NepkitError` → `CalendarDataError` / `DateError` →
  `InvalidDateError` / `DateOutOfRangeError`) as a comment/docstring, since
  `CalendarDataError` itself is import-time and not something to trigger here

**04_datetime_conversion.py**
- `BSDateTime(date, time)` construction
- `bs_datetime_to_ad_datetime` / `ad_datetime_to_bs_datetime` round trip
- Trigger and catch `InvalidDateError` from passing a tz-aware `datetime` to
  `ad_datetime_to_bs_datetime`
- A comment noting the NPT-only limitation (no timezone conversion; caller
  must `astimezone` + strip tzinfo first)

## `demo/README.md`

- One paragraph: what this is, who it's for.
- How to run: `uv run python demo/01_basic_conversion.py` from the repo root
  (uses the repo's own `.venv`, no install step), or plain `python
  demo/01_basic_conversion.py` if `typer`/`rich` are already available.
- A short index of the four scripts with a one-line description each.
- A note that scripts import `../src` directly via `_bootstrap.py`, so they
  always reflect local, possibly-unreleased changes to the library.

## Linting

No upfront `pyproject.toml` changes. After writing the scripts, run:

```bash
uv run ruff check --fix demo/
uv run ruff format demo/
```

Only add a `[tool.ruff.lint.per-file-ignores]` entry for `demo/**/*.py` if
`ruff check` still fails after `--fix` on something structural to the
narrated-script style (expected candidate: none, since `import _bootstrap`
followed by other imports are all import statements and won't trip `E402`).
`mypy`'s `files = ["src", "tests", "scripts"]` in `pyproject.toml` is left
unchanged — demo scripts are not type-checked.

## Verification

Run all four scripts (`uv run python demo/0N_*.py`) and confirm each executes
without error and its printed output matches what the comments claim it
demonstrates. No automated tests are added for `demo/` itself.
