# nepkit

```text
                      _     _  _
 _ __    ___   _ __  | | __(_)| |_
| '_ \  / _ \ | '_ \ | |/ /| || __|
| | | ||  __/ | |_) ||   < | || |_
|_| |_| \___| | .__/ |_|\_\|_| \__|
              |_|
```

Typed Bikram Sambat ↔ Gregorian date conversion for Python, as a library and a
command-line tool.

[![CI](https://github.com/akakritagya/nepkit/actions/workflows/ci.yml/badge.svg)](https://github.com/akakritagya/nepkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/nepkit)](https://pypi.org/project/nepkit/)
[![Python](https://img.shields.io/pypi/pyversions/nepkit)](https://pypi.org/project/nepkit/)
[![License](https://img.shields.io/pypi/l/nepkit)](https://github.com/akakritagya/nepkit/blob/main/LICENSE)

> **Status:** first release. The library and CLI both work and are tested; the
> API may still change before 1.0.

[**DEMO.md**](https://github.com/akakritagya/nepkit/blob/main/DEMO.md) walks
through every command, option, and failure mode with real captured output.

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

Requires Python 3.12+.

```bash
pip install nepkit       # library and CLI
uv add nepkit            # into a uv project
uv tool install nepkit   # the CLI on its own, isolated
```

[Typer](https://typer.tiangolo.com/) is the only direct dependency. The
calendar table is bundled, so nepkit never touches the network.

### Windows (Git Bash)

`uv tool install` puts `nepkit.exe` in uv's executable directory, which Git Bash
does not carry on `PATH` by default — the install reports success and the
command is still not found. Add the directory, then confirm:

```bash
uv tool install nepkit
uv tool dir --bin        # C:\Users\you\.local\bin
uv tool update-shell     # add it to the Windows user PATH
```

`uv tool update-shell` writes to the `HKCU\Environment` registry key rather than
to `~/.bashrc`, so only a **newly launched** tab sees it, and Windows does not
reliably notify running processes of the change
([uv#17331](https://github.com/astral-sh/uv/issues/17331)). If a fresh tab still
comes up empty, set it from bash instead — under Git Bash `$HOME` is
`/c/Users/you`, so this resolves to the same directory `uv tool dir --bin`
prints:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

Tab completion is the same one-liner as on Linux:

```bash
nepkit --install-completion
```

It appends a `source` line to `~/.bashrc` pointing at
`~/.bash_completions/nepkit.sh`, spelled as a Windows path (`C:\Users\...`).
That looks wrong inside a bash file, but MSYS2 resolves both spellings, so it
works as written.

## Library

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

```text
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

## CLI

`pip install` and `uv tool install` put a `nepkit` command on your PATH. `uv
add` installs into the project's `.venv` without activating it, so reach the
command with `uv run nepkit` — or activate the venv first.

```console
$ nepkit bs2ad 2081-04-15
2024-07-30

$ nepkit ad2bs 2024-07-30
2081-04-15

$ nepkit today
BS 2083-04-26
AD 2026-08-11

$ nepkit range
BS 2000-01-01 .. 2090-12-30  (years 2000-2090)
AD 1943-04-14 .. 2034-04-13
```

Direction is always explicit, and has to be: the BS and AD year numbers overlap
from 2000 to 2034, so `2024` is a valid year in both calendars and nothing
could reliably guess which one you meant.

### Interactive

Run `nepkit` with no arguments in a terminal and it clears the screen and opens
a session:

```console
$ nepkit
                      _     _  _
 _ __    ___   _ __  | | __(_)| |_
| '_ \  / _ \ | '_ \ | |/ /| || __|
| | | ||  __/ | |_) ||   < | || |_
|_| |_| \___| | .__/ |_|\_\|_| \__|
              |_|
nepkit v0.1.0 - Bikram Sambat (BS) <-> Gregorian (AD) date conversion
Today  BS 2083-04-26   AD 2026-08-11

Type a command, 'help', 'clear', or 'quit'.  Up/Down recalls history.

nepkit> today
BS 2083-04-26
AD 2026-08-11

nepkit> bs2ad 2081-04-15
2024-07-30

nepkit> quit
```

It accepts exactly the commands above — the same table, not a parallel
interface — so anything you can type at the shell works here unchanged. A bad
line reports the error and returns you to the prompt rather than ending the
session. `clear` (or `cls`) wipes the screen and redraws the banner. `quit`,
`exit`, `q`, and Ctrl-D all leave; Ctrl-C abandons the current line only.

Those four are prompt-only words, not subcommands — `nepkit clear` at a shell
stays a usage error rather than clearing your terminal.

Up and Down recall previous commands, and the usual `readline` editing keys
work (Ctrl-A, Ctrl-E, Ctrl-R, and so on). History lasts for the session and is
not written to disk. On Windows, where Python ships no `readline`, the prompt
works exactly the same minus the editing keys.

**Only on a terminal.** With stdin redirected — a pipeline, a script, CI —
`nepkit` prints help and exits 2 exactly as before, so nothing ever blocks
waiting for a prompt that isn't there.

### Calendars

```console
$ nepkit calbs 2081 4
        Shrawan 2081
    16 Jul - 16 Aug 2024
Sun Mon Tue Wed Thu Fri Sat
          1   2   3   4   5
  6   7   8   9  10  11  12
 13  14  15  16  17  18  19
 20  21  22  23  24  25  26
 27  28  29  30  31  32

$ nepkit calad 2024 7
         July 2024
Ashadh 17 - Shrawan 16, 2081
Sun Mon Tue Wed Thu Fri Sat
      1   2   3   4   5   6
  7   8   9  10  11  12  13
 14  15  16  17  18  19  20
 21  22  23  24  25  26  27
 28  29  30  31
```

Both default to the current month. A Gregorian month never lines up with a BS
month, so the subtitle names both ends of the span rather than pretending a
single corresponding month exists.

Grids are boxed and coloured on a terminal and plain when redirected, following
the same convention as `ls` and `git`. Force it either way with
`--color always|never|auto`.

On a terminal, today's date is picked out in bold bright magenta. The highlight
exists **only** in the coloured path: piped output is byte-for-byte
identical whether or not today falls in the month shown, so nothing parsing
stdout breaks on the one day a month it would otherwise appear. `--json`
reports it as a `today` field instead, which is `null` when today is elsewhere.

### Scripting

Every command takes `--json`:

```console
$ nepkit ad2bs 2008-05-28 --json
{"bs": "2065-02-15", "ad": "2008-05-28"}
```

**stdout carries results, stderr carries errors, and neither ever carries
both.** stdout contains no ANSI escapes unless you ask for colour explicitly,
so piping is always safe.

Exit codes come straight from the exception hierarchy, so a script can branch
without parsing any text:

| Code | Meaning | Example |
| --- | --- | --- |
| 0 | success | |
| 2 | usage error — bad flag or unknown command | `nepkit nosuchcommand` |
| 3 | not a real date | `nepkit bs2ad 2081-13-01` |
| 4 | a real date, but outside the bundled range | `nepkit bs2ad 2095-01-01` |

The 3/4 split is the one that matters when scripting: **4 is worth retrying
against another source, 3 never is.** Collapsing both into `1` would throw that
distinction away at exactly the boundary where it is most useful.

## Supported range

| Calendar | From | To |
| --- | --- | --- |
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
  the sourcing described in [`src/nepkit/data/DATA.md`](https://github.com/akakritagya/nepkit/blob/main/src/nepkit/data/DATA.md)
  stands behind the numbers themselves.

## Data provenance

[`src/nepkit/data/DATA.md`](https://github.com/akakritagya/nepkit/blob/main/src/nepkit/data/DATA.md) records where the calendar
table came from: two independently maintained sources with different authors,
languages, and conversion epochs, pinned at specific commits, diffed row by row
over all 91 years with no disagreements, and cross-checked by walking each
source forward from its own epoch to the anchor.

## Development

This project uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/akakritagya/nepkit
cd nepkit
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

### Releasing

Releases go to PyPI through
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — GitHub Actions
proves the repository's identity over OIDC, so no API token exists to leak or
rotate. Bump `version` in `pyproject.toml`, then:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

The tag runs `.github/workflows/publish.yml`, which re-runs the full gate,
refuses to continue if the tag disagrees with the packaged version, and only
then uploads. Run the workflow manually to rehearse against TestPyPI first.

## License

MIT — see [LICENSE](https://github.com/akakritagya/nepkit/blob/main/LICENSE).
