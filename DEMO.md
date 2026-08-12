# nepkit — demo

Every command, every option, and every failure mode.

All output below was captured by running the commands, not written by hand.
Captured 2026-08-11 against v0.1.0 — anything involving *today* will differ when
you run it, and is marked where that matters.

- [Conversions](#conversions)
- [Today and range](#today-and-range)
- [Calendars](#calendars)
- [Colour](#colour)
- [Interactive session](#interactive-session)
- [Errors and exit codes](#errors-and-exit-codes)
- [Scripting](#scripting)
- [Library](#library)
- [Help](#help)

---

## Conversions

Direction is always explicit. It has to be: BS 2000–2090 and AD 1943–2034
overlap numerically from 2000 to 2034, so `2024` is a valid year in *both*
calendars and nothing could reliably guess which you meant.

### BS → AD

```console
$ nepkit bs2ad 2081-04-15
2024-07-30
```

### AD → BS

```console
$ nepkit ad2bs 2024-07-30
2081-04-15
```

### Historical dates

Both of these are pinned by the tier-3 test suite against external sources —
see [`src/nepkit/data/DATA.md`](src/nepkit/data/DATA.md).

```console
$ nepkit ad2bs 2008-05-28      # Nepal declared a federal republic
2065-02-15

$ nepkit ad2bs 1951-02-18      # end of Rana rule / Democracy Day
2007-11-07
```

### As JSON

Both directions emit the same object, so a caller never has to know which way
the conversion ran.

```console
$ nepkit bs2ad 2081-04-15 --json
{"bs": "2081-04-15", "ad": "2024-07-30"}

$ nepkit ad2bs 2024-07-30 --json
{"bs": "2081-04-15", "ad": "2024-07-30"}
```

---

## Today and range

```console
$ nepkit today
BS 2083-04-26
AD 2026-08-11

$ nepkit today --json
{"bs": "2083-04-26", "ad": "2026-08-11"}
```

> Output varies with the date.

```console
$ nepkit range
BS 2000-01-01 .. 2090-12-30  (years 2000-2090)
AD 1943-04-14 .. 2034-04-13

$ nepkit range --json
{"bs": {"min": "2000-01-01", "max": "2090-12-30"}, "ad": {"min": "1943-04-14", "max": "2034-04-13"}}
```

`range` is what makes exit code 4 actionable: it tells a user who hit "out of
range" what *is* supported.

---

## Calendars

Both commands take an optional year and month, and default to the current one.

### A Bikram Sambat month

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
```

Note Shrawan has **32 days**. BS month lengths run from 29 to 32 with no
generating rule — that is the whole reason nepkit ships a data table rather
than an algorithm.

### A Gregorian month

The subtitle names both BS months the Gregorian month spans, because they never
line up and a single month name would be wrong.

```console
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

When the span crosses a BS **year** as well, both years are shown and the grid
centres itself under the wider heading:

```console
$ nepkit calad 2026 4
            April 2026
Chaitra 18 - Baisakh 17, 2082/2083
   Sun Mon Tue Wed Thu Fri Sat
                 1   2   3   4
     5   6   7   8   9  10  11
    12  13  14  15  16  17  18
    19  20  21  22  23  24  25
    26  27  28  29  30
```

### Current month

```bash
nepkit calbs          # this BS month
nepkit calad          # this Gregorian month
```

### Calendar data as JSON

`weeks` is Sunday-first with `null` for padding cells. `today` is the day of
this month to highlight, or `null` when today falls elsewhere.

```console
$ nepkit calbs 2081 4 --json
{"calendar": "bs", "title": "Shrawan 2081", "subtitle": "16 Jul - 16 Aug 2024", "today": null, "weeks": [[null, null, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18, 19], [20, 21, 22, 23, 24, 25, 26], [27, 28, 29, 30, 31, 32, null]]}
```

---

## Colour

On a terminal, grids are boxed and today's date is picked out in bold bright
magenta. Redirected, they are plain — the same convention `ls` and `git` follow.

```console
$ nepkit calbs 2081 9          # in a terminal
╭──────── Poush 2081 ─────────╮
│     16 Dec - 13 Jan 2025    │
│ Sun Mon Tue Wed Thu Fri Sat │
│       1   2   3   4   5   6 │
│   7   8   9  10  11  12  13 │
│  14  15  16  17  18  19  20 │
│  21  22  23  24  25  26  27 │
│  28  29                     │
╰─────────────────────────────╯
```

Force it either way:

```bash
nepkit calbs 2081 4 --color always    # box + colour even when piped
nepkit calbs 2081 4 --color never     # plain even on a terminal
nepkit calbs 2081 4 --color auto      # default
```

**stdout never contains ANSI escapes unless you ask for colour explicitly**, so
piping is always safe:

```console
$ nepkit calbs 2081 4 | grep -c $'\033'
0
```

The today-highlight lives only in the coloured path. Piped output is
byte-for-byte identical whether or not today falls in the month shown, so
nothing parsing stdout breaks on the one day a month a marker would appear.

---

## Interactive session

Run `nepkit` with no arguments in a terminal. It clears the screen and opens a
prompt:

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
nepkit> calbs 2081 9
╭──────── Poush 2081 ─────────╮
│     16 Dec - 13 Jan 2025    │
│ Sun Mon Tue Wed Thu Fri Sat │
│       1   2   3   4   5   6 │
│   7   8   9  10  11  12  13 │
│  14  15  16  17  18  19  20 │
│  21  22  23  24  25  26  27 │
│  28  29                     │
╰─────────────────────────────╯
nepkit> bs2ad 2095-01-01
BS year 2095 is outside the bundled range [2000, 2090]
nepkit> nosuchcmd
error: No such command 'nosuchcmd'.
nepkit> quit
```

It accepts **exactly** the commands above — the same table, not a parallel
interface. A bad line reports the error and returns you to the prompt rather
than ending the session.

| At the prompt | Effect |
| --- | --- |
| `help` | full command help |
| `clear` / `cls` | wipe the screen, redraw the banner |
| `quit` / `exit` / `q` | leave |
| Up / Down | recall previous commands |
| Ctrl-A / Ctrl-E / Ctrl-R | usual `readline` editing |
| Ctrl-C | abandon the current line, stay in the session |
| Ctrl-D | leave |

Those words are prompt-only, not subcommands — `nepkit clear` at a shell stays
a usage error rather than clearing your terminal.

**Only on a terminal.** With stdin redirected — a pipeline, a script, CI —
`nepkit` prints help and exits 2, so nothing ever blocks on a prompt that
isn't there:

```console
$ nepkit < /dev/null
Usage: nepkit [OPTIONS] COMMAND [ARGS]...
...
$ echo $?
2
```

History lasts for the session and is not written to disk. On Windows, where
Python ships no `readline`, the prompt works the same minus the editing keys.

---

## Errors and exit codes

| Code | Meaning |
| --- | --- |
| 0 | success |
| 2 | usage error — bad flag or unknown command |
| 3 | not a real date |
| 4 | a real date, but outside the bundled range |

**3 and 4 are separate on purpose.** `4` is worth retrying against another
source; `3` never is. Collapsing both into `1` would throw that away at exactly
the boundary where a caller has no exception object to inspect.

### Exit 3 — not a real date

```console
$ nepkit bs2ad 2081-13-01
BS month 13 is outside [1, 12]                          # stderr, exit 3

$ nepkit bs2ad 2081-04-33
BS 2081-04: day 33 is outside [1, 32]                   # stderr, exit 3

$ nepkit bs2ad not-a-date
'not-a-date' is not a date in YYYY-MM-DD form           # stderr, exit 3

$ nepkit ad2bs 2024-13-01
AD 2024-13-01 is not a real Gregorian date              # stderr, exit 3

$ nepkit ad2bs 2024-02-30
AD 2024-02-30 is not a real Gregorian date              # stderr, exit 3
```

Malformed input exits the same way in both directions. Typer could have parsed
the AD side natively, which would have made identical garbage exit 2 for
`ad2bs` and 3 for `bs2ad`.

### Exit 4 — real, but unsupported

```console
$ nepkit bs2ad 2095-01-01
BS year 2095 is outside the bundled range [2000, 2090]  # stderr, exit 4

$ nepkit ad2bs 2040-01-01
AD 2040-01-01 is outside the convertible window 1943-04-14 through 2034-04-13

$ nepkit calbs 2095 1
BS year 2095 is outside the bundled range [2000, 2090]  # stderr, exit 4

$ nepkit calad 2034 4
AD 2034-04 is not fully inside the convertible window 1943-04-14 through 2034-04-13
```

`calad` refuses a month it cannot draw in full — April 1943 is convertible only
from the 14th, April 2034 only to the 13th. A grid with holes in it is harder
to explain than a refusal naming the window.

### Exit 2 — usage

```console
$ nepkit nosuchcommand ; echo "exit $?"
exit 2
$ nepkit bs2ad ; echo "exit $?"
exit 2
$ nepkit bs2ad --bogus ; echo "exit $?"
exit 2
```

(Usage text omitted above; it goes to stderr.)

### Stream discipline

**stdout carries results, stderr carries errors, and neither ever carries
both.** Every error above writes to stderr with stdout completely empty:

```console
$ nepkit bs2ad 2095-01-01 2>/dev/null | wc -c
0
```

---

## Scripting

### Branch on the exit code

```bash
for d in 2081-04-15 2095-01-01 2081-13-01; do
  if out=$(nepkit bs2ad "$d" 2>/dev/null); then
    echo "$d -> $out"
  else
    case $? in
      3) echo "$d -> not a real date (3)" ;;
      4) echo "$d -> outside nepkit's range (4)" ;;
      *) echo "$d -> usage error" ;;
    esac
  fi
done
```

```console
2081-04-15 -> 2024-07-30
2095-01-01 -> outside nepkit's range (4)
2081-13-01 -> not a real date (3)
```

### Parse the JSON

```console
$ nepkit today --json | jq -r .bs
2083-04-26

$ nepkit calbs 2081 4 --json | jq '[.weeks[][] | select(. != null)] | length'
32
```

---

## Library

The CLI is a thin layer over the package; everything it does is available
directly.

```python
from datetime import date

from nepkit import BSDate, ad_to_bs, bs_to_ad, days_in_month, BS_MONTH_NAMES

bs_to_ad(BSDate(2081, 4, 15))  # datetime.date(2024, 7, 30)
ad_to_bs(date(2024, 7, 30))  # BSDate(year=2081, month=4, day=15)
days_in_month(2081, 4)  # 32
BS_MONTH_NAMES[3]  # 'Shrawan'
```

`BSDate` validates on construction, so holding one means it is a real date in
the supported range:

```python
BSDate(2081, 4, 33)  # raises InvalidDateError
BSDate(2081, 13, 1)  # raises InvalidDateError
BSDate(2095, 1, 1)  # raises DateOutOfRangeError
```

`ad_to_bs` takes a `datetime.date`, so a malformed Gregorian date is impossible
by construction — Python's own constructor rejects it before nepkit is
involved.

```text
NepkitError
├── CalendarDataError   the bundled table is malformed; raised at import
└── DateError
    ├── InvalidDateError      not a real BS date
    └── DateOutOfRangeError   real, but outside the bundled range
```

Catch `DateError` if you only need "the user gave me something I can't
convert".

---

## Help

```console
$ nepkit --help
 Usage: nepkit [OPTIONS] COMMAND [ARGS]...

 Bikram Sambat (BS) <-> Gregorian (AD) date conversion.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ bs2ad  Convert a Bikram Sambat date to Gregorian.                            │
│ ad2bs  Convert a Gregorian date to Bikram Sambat.                            │
│ today  Print today's date in both calendars.                                 │
│ range  Print the date range nepkit has data for.                             │
│ calbs  Display a Bikram Sambat month.                                        │
│ calad  Display a Gregorian month.                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Per-command help works too:

```console
$ nepkit calbs --help
 Usage: nepkit calbs [OPTIONS] [year] [month]

 Display a Bikram Sambat month.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   year       <int>  Year. Defaults to the current one.                       │
│   month      <int>  Month, 1-12. Defaults to the current one.                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                              Emit machine-readable JSON.              │
│ --color        <auto|always|never>  When to colourise the grid.              │
│                                     [default: auto]                          │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## What nepkit will not do

- **Extrapolate past the table.** There is no rule to extrapolate with; dates
  beyond BS 2000–2090 would have to be invented, so they raise instead.
- **Guess a direction.** See the overlap note at the top.
- **Time of day, timezones, Nepali month names in Devanagari, or Nepali
  numerals.** Dates only.

Correctness rests on the bundled table, and the test suite cannot prove it:
both conversion directions read the same data, so a wrong month length cancels
out exactly. That is what the sourcing in
[`src/nepkit/data/DATA.md`](src/nepkit/data/DATA.md) and the external-oracle
tests in [`tests/test_oracle.py`](tests/test_oracle.py) are for.
