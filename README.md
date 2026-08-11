# nepkit

Typed Bikram Sambat ↔ Gregorian date conversion for Python, as a library and
(eventually) a CLI.

> **Status:** the conversion library works and is tested. The `nepkit` CLI is
> wired up but exposes no commands yet, and there is no PyPI release — install
> from source for now.

## Why

Bikram Sambat is Nepal's official calendar, and converting to and from it is not
arithmetic. Gregorian leap years follow a rule you can write down; BS month
lengths do not. They vary between 29 and 32 days with no generating formula, are
fixed by observation, and are published by Nepal's Panchanga authority. Every
correct converter is therefore a **lookup table plus one verified anchor date** —
which means the data matters more than the code, and most of the work in this
repo went into the data.

The existing Python options are small, mostly unmaintained packages with
undocumented year ranges, no type hints, and no statement of where their numbers
came from or how far they can be trusted. nepkit aims to be one typed, tested
converter that is explicit about all three.

## Install

Requires Python 3.12+. This project uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/akakritagya/nepkit
cd nepkit
uv sync
```

There is no published package yet, so `pip install nepkit` will not work.

## Usage

```python
from datetime import date

from nepkit import BSDate, ad_to_bs, bs_to_ad

bs_to_ad(BSDate(2081, 4, 15))  # date(2024, 7, 30)
ad_to_bs(date(2024, 7, 30))  # BSDate(year=2081, month=4, day=15)
```

`BSDate` validates on construction, so if you are holding one it is a real date
in the supported range:

```python
from nepkit import BSDate, days_in_month

days_in_month(2081, 4)  # 32
days_in_month(2081, 9)  # 29

BSDate(2081, 4, 33)  # raises InvalidDateError
BSDate(2081, 13, 1)  # raises InvalidDateError
BSDate(2095, 1, 1)  # raises DateOutOfRangeError
```

`ad_to_bs` takes a `datetime.date`, so a malformed Gregorian date is impossible
by construction — Python's own constructor rejects it before nepkit is involved.

### Errors

```
NepkitError
├── CalendarDataError   the bundled table is malformed; raised at import
└── DateError
    ├── InvalidDateError      not a real BS date (month 13, day 33, ...)
    └── DateOutOfRangeError   a real date, but outside the bundled range
```

The split between the last two is the one that earns its keep. BS 2095-03-12 is
a perfectly real date that nepkit simply has no data for, and a caller can
reasonably catch that and fall back or report the supported range. BS 2081-13-01
is not a date at all, and catching it is always a mistake. Catch `DateError` if
you only need "the user gave me something I can't convert".

### CLI

```bash
uv run nepkit --help
```

The entry point exists but has no commands yet; `nepkit date` conversion is the
first one planned.

## Supported range

| | From | To |
|---|---|---|
| Bikram Sambat | 2000-01-01 | 2090-12-30 |
| Gregorian | 1943-04-14 | 2034-04-13 |

That is 91 years, 33,238 days. Anything outside it raises `DateOutOfRangeError`
rather than extrapolating, because there is no rule to extrapolate with — dates
beyond the table would have to be invented.

The bounds are computed from the bundled data, not written down separately, so
extending the table moves them automatically.

## Design decisions

**One anchor, everything else derived.** The whole library hangs on a single
verified correspondence: BS 2000-01-01 = AD 1943-04-14. That is the only
Gregorian fact in the package that cannot be computed, because month lengths
alone cannot tell you where the calendar sits against the Gregorian one. Every
other bound — the last BS date, both ends of the AD window — is derived from it
plus the table. A second hardcoded date would be free to drift out of sync, and
the failure would be silent and total.

**Both directions collapse to a day count.** A BS date becomes "days since the
anchor", integer arithmetic happens there, and the result expands out the other
side. `datetime.date` is already a correct expander for the Gregorian side, so
`bs_to_ad` is one line; the real work is the inverse, which has no equivalent in
the standard library.

**Types instead of validation where possible.** `ad_to_bs` accepts a
`datetime.date` rather than three integers, which removes an entire error class
from its contract at no cost.

## Limitations

- **Dates only.** No time of day, no timezones, no Nepali-language month names
  or numeral formatting.
- **The range is hard-bounded** at BS 2000–2090 and will not extrapolate.
- **Correctness rests on the data, and the tests cannot prove it.** The test
  suite verifies self-consistency exhaustively — every one of the 33,238 days
  round-trips, and consecutive day counts produce consecutive dates. But both
  directions read the same table, so a wrong month length cancels out exactly
  and every property still passes. This was verified by deliberately corrupting
  the table: all properties passed while conversions were silently wrong. Only
  the sourcing described in [`src/nepkit/data/DATA.md`](src/nepkit/data/DATA.md)
  stands behind the numbers themselves.

## Data provenance

[`src/nepkit/data/DATA.md`](src/nepkit/data/DATA.md) records where the calendar
table came from: two independently maintained sources with different authors,
languages, and conversion epochs, pinned at specific commits, diffed row by row
over all 91 years with no disagreements, and cross-checked by walking each
source forward from its own epoch to the anchor.

## Development

```bash
uv sync --group dev          # pytest, ruff, mypy, pre-commit
uv run pytest                # run tests
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # type check
```

```bash
uv run pre-commit install                         # lint/format/type-check on commit
uv run pre-commit install --hook-type commit-msg  # enforce Conventional Commits
uv run pre-commit install --hook-type pre-push    # full test suite before push
```

`pre-commit` runs lint, format, and type-check on every commit; blocks large
files, private keys, and direct commits to `main`; runs the full `pytest` suite
before `push` (not on every commit — too slow to survive contact with a growing
suite); and enforces
[Conventional Commits](https://www.conventionalcommits.org/) on the message.

## License

MIT — see [LICENSE](LICENSE).
