"""Human text in and out: parse_*_date/format_*_date, month/weekday names, Devnagari.

Run: uv run python demo/02_parsing_and_formatting.py
"""

from datetime import date

import _bootstrap  # noqa: F401 -- inserts ../src onto sys.path as a side effect

from nepkit import (
    BSDate,
    InvalidDateError,
    bs_month_name,
    format_ad_date,
    format_bs_date,
    parse_ad_date,
    parse_ad_month,
    parse_bs_date,
    parse_bs_month,
    to_devnagari_numerals,
    weekday_name,
)

# parse_bs_date accepts strict "YYYY-MM-DD" ...
print(f'parse_bs_date("2081-04-15") -> {parse_bs_date("2081-04-15")}')

# ... or "D Month YYYY", matched case-insensitively against BS_MONTH_NAMES's
# one spelling *or* a common romanisation variant -- "Baishakh" here, not
# just BS_MONTH_NAMES's "Baisakh".
print(f'parse_bs_date("15 Baishakh 2081") -> {parse_bs_date("15 Baishakh 2081")}')

# parse_ad_date takes the same two shapes on the Gregorian side.
print(f'parse_ad_date("2024-07-30") -> {parse_ad_date("2024-07-30")}')
print(f'parse_ad_date("30 Jul 2024") -> {parse_ad_date("30 Jul 2024")}')

# BSDate mirrors datetime.date's string handling.
bs = BSDate(2081, 4, 15)
print(f"str(BSDate(2081, 4, 15)) -> {bs!s}")
print(f'BSDate.fromisoformat("2081-04-15") -> {BSDate.fromisoformat("2081-04-15")}')

# format_bs_date's default is the same ISO layout; named=True switches to
# "D Month YYYY", and devnagari=True renders both the digits and (when named)
# the month name in Devnagari.
print(f"format_bs_date(bs) -> {format_bs_date(bs)}")
print(f"format_bs_date(bs, named=True) -> {format_bs_date(bs, named=True)}")
print(
    "format_bs_date(bs, named=True, devnagari=True) -> "
    f"{format_bs_date(bs, named=True, devnagari=True)}"
)

# format_ad_date mirrors it on the Gregorian side, but its month abbreviation
# stays Latin either way -- nepkit has no Devnagari names for Gregorian
# months.
ad = date(2024, 7, 30)
print(f"format_ad_date(ad, named=True) -> {format_ad_date(ad, named=True)}")
print(
    "format_ad_date(ad, named=True, devnagari=True) -> "
    f"{format_ad_date(ad, named=True, devnagari=True)}"
)

# The pieces format_bs_date/format_ad_date are built from, usable on their own.
print(f"bs_month_name(4) -> {bs_month_name(4)}")
print(f"bs_month_name(4, devnagari=True) -> {bs_month_name(4, devnagari=True)}")
print(f"weekday_name(ad) -> {weekday_name(ad)}")
print(f'to_devnagari_numerals("2081-04-15") -> {to_devnagari_numerals("2081-04-15")}')

# parse_bs_date/parse_ad_date parse a full date; parse_bs_month/parse_ad_month
# parse just the month half the same way -- a plain number, a name, or (BS
# side) a romanisation variant, all case-insensitively. Useful on their own
# for something like the CLI's calbs/calad, which take a bare month argument.
print(f'parse_bs_month("Shrawan") -> {parse_bs_month("Shrawan")}')
print(f'parse_bs_month("sawan") -> {parse_bs_month("sawan")}')  # romanisation variant
print(f'parse_ad_month("Jul") -> {parse_ad_month("Jul")}')
print(f'parse_ad_month("july") -> {parse_ad_month("july")}')

# Parsing fails the same way construction does: syntactically date-shaped
# text with an unrecognised month name is an InvalidDateError, not a
# ValueError -- one exception type to catch regardless of where the bad
# input entered the library.
try:
    parse_bs_date("15 Notamonth 2081")
except InvalidDateError as exc:
    print(f'parse_bs_date("15 Notamonth 2081") -> InvalidDateError: {exc}')

# Footgun worth knowing about, not demonstrating by triggering it: BSDate's
# isoformat() produces "YYYY-MM-DD", the ISO 8601 *layout*, but applied to a
# Bikram Sambat date -- it is not an ISO 8601 date. datetime.date.fromisoformat
# will happily accept it and silently return a different, wrong Gregorian day.
# bs.isoformat() is only ever meaningful alongside something that says it's BS.
