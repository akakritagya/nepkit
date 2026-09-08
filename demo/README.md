# nepkit demo

Small, narrated, standalone scripts that exercise `nepkit`'s public library
API, one use case per file. Meant to be read top-to-bottom and run
individually — for someone learning or evaluating the library, not for the
CLI (see the repo's own [DEMO.md](../DEMO.md) for that).

## Running

From the repo root, using the repo's own `.venv` (no install step needed):

```bash
uv run python demo/01_basic_conversion.py
```

Or, with that `.venv` already active (or `typer`/`rich` otherwise available):

```bash
python demo/01_basic_conversion.py
```

Each script imports `_bootstrap.py` first, which puts `../src` on `sys.path`
— so every script always runs against this checkout's local source, not an
installed copy, even one with unreleased changes.

## Scripts

| Script | Demonstrates |
| --- | --- |
| [`01_basic_conversion.py`](01_basic_conversion.py) | `BSDate` construction/validation, `bs_to_ad`/`ad_to_bs`, `days_in_month`, the supported year range |
| [`02_parsing_and_formatting.py`](02_parsing_and_formatting.py) | `parse_bs_date`/`parse_ad_date`, `format_bs_date`/`format_ad_date`, month/weekday names, Devnagari numerals |
| [`03_error_handling.py`](03_error_handling.py) | The `NepkitError` hierarchy, and why `InvalidDateError` vs. `DateOutOfRangeError` is worth catching separately |
| [`04_datetime_conversion.py`](04_datetime_conversion.py) | `BSDateTime`, `ad_datetime_to_bs_datetime`/`bs_datetime_to_ad_datetime`, and why a tz-aware `datetime` is rejected |
