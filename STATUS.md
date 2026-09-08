# Status

Published, pre-1.0. The library and CLI both work and are tested, but the
API and the CLI's output shapes may still change before 1.0. Pin a version
if you script against `nepkit`'s stdout, or use `--json` instead — that
shape is the one thing this file will never break without a major version.

See [DEMO.md](https://github.com/akakritagya/nepkit/blob/main/DEMO.md) for
every command's current output, captured live.

## Unreleased

Nothing yet.

## v0.4.0 — 2026-09-08

- **Promoted the CLI's date parsing/formatting into the library**
  ([#39](https://github.com/akakritagya/nepkit/pull/39), 2026-09-08).
  `BSDate`/`BSDateTime` gained `isoformat()`/`fromisoformat()`/`__str__`
  (their `repr` is unchanged), and `nepkit` now exports
  `parse_bs_date`/`parse_ad_date`, `format_bs_date`/`format_ad_date`,
  `parse_bs_month`/`parse_ad_month`, `bs_month_name`, `weekday_name`, and
  `to_devnagari_numerals`.
- **Month-name input widened**, on the CLI and in the library alike (same
  PR): `bs2ad`/`ad2bs`/`calbs`/`parse_bs_date`/`parse_bs_month` now accept
  common romanisation variants (`Baishakh` alongside `Baisakh`, `Sawan`
  alongside `Shrawan`, ...) and Devnagari month names, not just the one
  spelling `BS_MONTH_NAMES` prints. Output is unaffected, and nothing that
  parsed before stops parsing.
- **Locale fix** (same PR): Gregorian month names/abbreviations shown or
  parsed anywhere in nepkit (`calad`'s grid title, `bs2ad`/`ad2bs`'s AD
  line) no longer read the process locale — they were briefly,
  inconsistently locale-sensitive under a non-English `LC_TIME`; they are
  now always English, matching the weekday names' existing convention.
- **`calbs`/`calad` accept a month name**
  ([#38](https://github.com/akakritagya/nepkit/pull/38), 2026-09-08):
  `Shrawan`/`July`/`Jul` alongside `1`-`12`, matched case-insensitively.
  Their output and `--script` support (none) are unchanged.
- **`bs2ad`/`ad2bs` accept named dates and print them**
  ([#37](https://github.com/akakritagya/nepkit/pull/37), 2026-09-08): the
  `BS_DATE`/`AD_DATE` argument now also accepts `"D Month YYYY"` (e.g.
  `"1 Baisakh 2083"`, `"1 Jan 2000"`), the month matched
  case-insensitively, alongside the original `YYYY-MM-DD`. Their
  plain-text line changed from `2024-07-30 Tue` to
  `AD 30 Jul 2024 (2024-07-30) Tue` (named date, ISO form in parentheses,
  weekday) — `--json`'s `bs`/`ad`/`weekday` fields are unchanged.
- **Interactive banner's date line switched to named dates**
  ([#36](https://github.com/akakritagya/nepkit/pull/36), 2026-09-08), the
  same way `today` did just before it.
- **`today` switched to named dates, and to Devnagari by default**
  ([#35](https://github.com/akakritagya/nepkit/pull/35), 2026-09-08):
  plain-text dates changed from numeric (`2083-04-27`) to named
  (`27 Shrawan 2083`), and `--script devnagari` became the default, so
  plain `nepkit today` now prints Devnagari on the BS line unless you pass
  `--script latin`. `today --json`'s numeric `bs`/`ad` fields are
  unchanged, with named forms added alongside as `bs_text`/`ad_text`.

## v0.2.0 — 2026-08-12

- Weekday appended to `bs2ad`, `ad2bs`, and `today`'s plain-text output.
