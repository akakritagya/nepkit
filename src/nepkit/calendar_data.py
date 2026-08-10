"""Bundled Bikram Sambat calendar table: validation, loading, and lookups.

See src/nepkit/data/DATA.md for where the underlying numbers came from.
"""

import json
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

MIN_BS_YEAR: Final[int] = _YEARS[0].year
MAX_BS_YEAR: Final[int] = _YEARS[-1].year


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


def days_from_anchor(year: int, month: int, day: int) -> int:
    """Days from ANCHOR to the given BS date. The one primitive bs_to_ad needs."""
    max_day = days_in_month(year, month)  # validates year and month
    if not (1 <= day <= max_day):
        raise InvalidDateError(f"BS {year}-{month:02d}: day {day} is outside [1, {max_day}]")
    days_before_month = sum(_BY_YEAR[year].months[: month - 1])
    return _CUMULATIVE_OFFSET[year] + days_before_month + (day - 1)
