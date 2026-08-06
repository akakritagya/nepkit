"""Bundled Bikram Sambat calendar table: validation, loading, and lookups.

See src/nepkit/data/DATA.md for where the underlying numbers came from.
"""

import json
from dataclasses import dataclass
from datetime import date
from importlib import resources
from itertools import pairwise

from nepkit.exceptions import CalendarDataError, DateOutOfRangeError, InvalidDateError

_MONTHS_PER_YEAR = 12
_MIN_DAYS_IN_MONTH = 29
_MAX_DAYS_IN_MONTH = 32
_MIN_DAYS_IN_YEAR = 365
_MAX_DAYS_IN_YEAR = 366


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
        rows: list[dict[str, object]] = json.loads(raw)
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
        if current.year != previous.year + 1:
            raise CalendarDataError(
                f"calendar.json has a gap: BS {previous.year} is followed by BS {current.year}"
            )


def _build_cumulative_offsets(years: tuple[BSYearData, ...]) -> dict[int, int]:
    """Days from the anchor to the start of each BS year, so bs_to_ad never sums a range."""
    offsets: dict[int, int] = {}
    running = 0
    for year_data in years:
        offsets[year_data.year] = running
        running += sum(year_data.months)
    return offsets


_YEARS = _load_years()
_check_contiguous(_YEARS)
_BY_YEAR: dict[int, BSYearData] = {y.year: y for y in _YEARS}
_CUMULATIVE_OFFSET: dict[int, int] = _build_cumulative_offsets(_YEARS)

MIN_BS_YEAR: int = _YEARS[0].year
MAX_BS_YEAR: int = _YEARS[-1].year

# ANCHOR_BS and ANCHOR_AD are one fact (see data/DATA.md) pinned as two literals
# because ANCHOR_AD cannot be derived from calendar.json's month lengths alone.
# The assertion below keeps them from silently drifting apart if calendar.json's
# first year ever changes.
ANCHOR_BS: tuple[int, int, int] = (2000, 1, 1)
ANCHOR_AD: date = date(1943, 4, 14)

if ANCHOR_BS[0] != MIN_BS_YEAR:
    raise CalendarDataError(
        f"ANCHOR_BS year {ANCHOR_BS[0]} does not match calendar.json's first year "
        f"{MIN_BS_YEAR} — the anchor and the bundled data have gone out of sync"
    )


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
    """Days from ANCHOR_BS to the given BS date. The one primitive bs_to_ad needs."""
    max_day = days_in_month(year, month)  # validates year and month
    if not (1 <= day <= max_day):
        raise InvalidDateError(f"BS {year}-{month:02d}: day {day} is outside [1, {max_day}]")
    days_before_month = sum(_BY_YEAR[year].months[: month - 1])
    return _CUMULATIVE_OFFSET[year] + days_before_month + (day - 1)
