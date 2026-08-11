"""Bundled Bikram Sambat calendar table: validation, loading, and lookups.

See src/nepkit/data/DATA.md for where the underlying numbers came from.
"""

import json
from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from importlib import resources
from itertools import pairwise
from typing import Final

from nepkit.exceptions import CalendarDataError, DateOutOfRangeError, InvalidDateError

_MONTHS_PER_YEAR: Final[int] = 12
_MIN_DAYS_IN_MONTH: Final[int] = 29
_MAX_DAYS_IN_MONTH: Final[int] = 32
_MIN_DAYS_IN_YEAR: Final[int] = 365
_MAX_DAYS_IN_YEAR: Final[int] = 366


@dataclass(frozen=True, slots=True)
class BSYearData:
    """One BS year's month lengths, validated on construction."""

    year: int
    months: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.months) != _MONTHS_PER_YEAR:
            raise CalendarDataError(
                f"BS {self.year}: expected {_MONTHS_PER_YEAR} months, got {len(self.months)}"
            )
        for month, days in enumerate(self.months, start=1):
            if not (_MIN_DAYS_IN_MONTH <= days <= _MAX_DAYS_IN_MONTH):
                raise CalendarDataError(
                    f"BS {self.year} month {month}: {days} days is outside "
                    f"[{_MIN_DAYS_IN_MONTH}, {_MAX_DAYS_IN_MONTH}]"
                )
        total = sum(self.months)
        if not (_MIN_DAYS_IN_YEAR <= total <= _MAX_DAYS_IN_YEAR):
            raise CalendarDataError(
                f"BS {self.year}: year totals {total} days, outside "
                f"[{_MIN_DAYS_IN_YEAR}, {_MAX_DAYS_IN_YEAR}]"
            )


def _load_years() -> tuple[BSYearData, ...]:
    raw = resources.files("nepkit.data").joinpath("calendar.json").read_text(encoding="utf-8")
    try:
        rows: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CalendarDataError(f"calendar.json is not valid JSON: {exc}") from exc

    if not isinstance(rows, list) or not rows:
        raise CalendarDataError("calendar.json must contain a non-empty list of year rows")

    years: list[BSYearData] = []
    for row in rows:
        if not isinstance(row, dict) or "year" not in row or "months" not in row:
            raise CalendarDataError(f"calendar.json row is malformed: {row!r}")
        year, months = row["year"], row["months"]
        if (
            not isinstance(year, int)
            or not isinstance(months, list)
            or not all(isinstance(m, int) for m in months)
        ):
            raise CalendarDataError(f"calendar.json row is malformed: {row!r}")
        years.append(BSYearData(year=year, months=tuple(months)))

    years.sort(key=lambda y: y.year)
    return tuple(years)


def _check_contiguous(years: tuple[BSYearData, ...]) -> None:
    for previous, current in pairwise(years):
        if current.year == previous.year:
            raise CalendarDataError(f"calendar.json has a duplicate row for BS {current.year}")
        if current.year != previous.year + 1:
            raise CalendarDataError(
                f"calendar.json has a gap: BS {previous.year} is followed by BS {current.year}"
            )


def _build_cumulative_offsets(years: tuple[BSYearData, ...]) -> Mapping[int, int]:
    """Days from the anchor to the start of each BS year, so bs_to_ad never sums a range."""
    offsets: dict[int, int] = {}
    running = 0
    for year_data in years:
        offsets[year_data.year] = running
        running += sum(year_data.months)
    return offsets


_YEARS: Final[tuple[BSYearData, ...]] = _load_years()
_check_contiguous(_YEARS)
_BY_YEAR: Final[Mapping[int, BSYearData]] = {y.year: y for y in _YEARS}
_CUMULATIVE_OFFSET: Final[Mapping[int, int]] = _build_cumulative_offsets(_YEARS)
# The same offsets as a sorted sequence. _CUMULATIVE_OFFSET answers "which offset
# does this year start at?"; this answers the inverse, "which year contains this
# offset?", which is a bisect over boundaries and not a dict lookup at all.
_YEAR_START_OFFSETS: Final[tuple[int, ...]] = tuple(_CUMULATIVE_OFFSET[y.year] for y in _YEARS)

MIN_BS_YEAR: Final[int] = _YEARS[0].year
MAX_BS_YEAR: Final[int] = _YEARS[-1].year

# Derived from the table, never written down: the number of days the bundled
# range covers. Every other bound (the last BS date, the AD window in convert)
# is computed from this, so extending calendar.json moves them all at once.
TOTAL_DAYS: Final[int] = sum(sum(y.months) for y in _YEARS)


@dataclass(frozen=True, slots=True)
class Anchor:
    """The one verified BS↔AD correspondence the whole module hangs on."""

    bs_year: int
    bs_month: int
    bs_day: int
    ad_date: date


def _check_anchor_is_first_day_of_min_year(anchor: Anchor, min_year: int) -> None:
    """The cumulative offset table starts at min_year, so the anchor must be its 1/1."""
    if (anchor.bs_year, anchor.bs_month, anchor.bs_day) != (min_year, 1, 1):
        raise CalendarDataError(
            f"ANCHOR {anchor.bs_year}-{anchor.bs_month:02d}-{anchor.bs_day:02d} is not "
            f"the first day of calendar.json's first year (BS {min_year}) — the "
            "cumulative offset table is built starting from that first year, so the "
            "anchor must be its first day or every offset is silently wrong"
        )


# ANCHOR pins one verified BS<->AD correspondence (see data/DATA.md) as a single
# fact, rather than two literals that could drift apart, because the AD side
# cannot be derived from calendar.json's month lengths alone.
ANCHOR: Final[Anchor] = Anchor(bs_year=2000, bs_month=1, bs_day=1, ad_date=date(1943, 4, 14))

_check_anchor_is_first_day_of_min_year(ANCHOR, MIN_BS_YEAR)


def days_in_month(year: int, month: int) -> int:
    """Number of days in the given BS month. Raises on an out-of-range year or bad month."""
    if not (MIN_BS_YEAR <= year <= MAX_BS_YEAR):
        raise DateOutOfRangeError(
            f"BS year {year} is outside the bundled range [{MIN_BS_YEAR}, {MAX_BS_YEAR}]"
        )
    if not (1 <= month <= _MONTHS_PER_YEAR):
        raise InvalidDateError(f"BS month {month} is outside [1, {_MONTHS_PER_YEAR}]")
    return _BY_YEAR[year].months[month - 1]


def check_bs_date(year: int, month: int, day: int) -> None:
    """Raise unless (year, month, day) is a real BS date inside the bundled range."""
    max_day = days_in_month(year, month)  # validates year and month
    if not (1 <= day <= max_day):
        raise InvalidDateError(f"BS {year}-{month:02d}: day {day} is outside [1, {max_day}]")


def days_from_anchor(year: int, month: int, day: int) -> int:
    """Days from ANCHOR to the given BS date. The one primitive bs_to_ad needs."""
    check_bs_date(year, month, day)
    days_before_month = sum(_BY_YEAR[year].months[: month - 1])
    return _CUMULATIVE_OFFSET[year] + days_before_month + (day - 1)


def bs_from_days(days: int) -> tuple[int, int, int]:
    """Inverse of days_from_anchor: the BS date that many days after ANCHOR."""
    if not (0 <= days < TOTAL_DAYS):
        raise DateOutOfRangeError(
            f"{days} days from the anchor is outside [0, {TOTAL_DAYS}) — the bundled "
            f"table covers BS {MIN_BS_YEAR} through {MAX_BS_YEAR}"
        )
    index = bisect_right(_YEAR_START_OFFSETS, days) - 1
    year_data = _YEARS[index]
    remainder = days - _YEAR_START_OFFSETS[index]
    for month, length in enumerate(year_data.months, start=1):
        if remainder < length:
            return (year_data.year, month, remainder + 1)
        remainder -= length
    # Unreachable: the bounds check above puts `days` inside the span, and bisect
    # picks the year containing it, so `remainder` is always < that year's total.
    raise AssertionError(f"bs_from_days({days}) escaped BS {year_data.year}'s months")
