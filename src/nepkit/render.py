"""Month-grid construction and plain-text rendering.

Pure functions: no I/O, no terminal detection, no CLI framework. The CLI layer
decides where output goes and whether to dress it up; everything about *what*
the grid contains is decided and tested here.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from nepkit.calendar_data import BS_MONTH_NAMES, days_in_month
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import DateOutOfRangeError

WEEKDAY_HEADER: Final[str] = "Sun Mon Tue Wed Thu Fri Sat"
_DAYS_PER_WEEK: Final[int] = 7
_CELL_WIDTH: Final[int] = 3


@dataclass(frozen=True, slots=True)
class MonthGrid:
    """One month laid out as Sunday-first weeks, plus its two heading lines."""

    title: str
    subtitle: str
    weeks: tuple[tuple[int | None, ...], ...]


def _sunday_first_index(day: date) -> int:
    """Python weeks start Monday; Nepali (and `cal`) calendars start Sunday."""
    return (day.weekday() + 1) % _DAYS_PER_WEEK


def _build_weeks(lead_blanks: int, total_days: int) -> tuple[tuple[int | None, ...], ...]:
    cells: list[int | None] = [None] * lead_blanks + list(range(1, total_days + 1))
    while len(cells) % _DAYS_PER_WEEK:
        cells.append(None)
    return tuple(
        tuple(cells[start : start + _DAYS_PER_WEEK])
        for start in range(0, len(cells), _DAYS_PER_WEEK)
    )


def bs_month_grid(year: int, month: int) -> MonthGrid:
    """Lay out a Bikram Sambat month, cross-referenced to the Gregorian dates it spans."""
    first_bs = BSDate(year=year, month=month, day=1)  # validates year and month
    total_days = days_in_month(year, month)
    first_ad = bs_to_ad(first_bs)
    last_ad = first_ad + timedelta(days=total_days - 1)

    span = f"{first_ad.strftime('%d %b')} - {last_ad.strftime('%d %b %Y')}"
    return MonthGrid(
        title=f"{BS_MONTH_NAMES[month - 1]} {year}",
        subtitle=span,
        weeks=_build_weeks(_sunday_first_index(first_ad), total_days),
    )


def ad_month_grid(year: int, month: int) -> MonthGrid:
    """Lay out a Gregorian month, cross-referenced to the BS months it spans.

    A Gregorian month never lines up with a BS month, so the subtitle names
    both ends rather than pretending there is a single corresponding month.
    """
    if not (1 <= month <= 12):
        raise DateOutOfRangeError(f"AD month {month} is outside [1, 12]")
    total_days = calendar.monthrange(year, month)[1]
    first_ad = date(year, month, 1)
    last_ad = date(year, month, total_days)

    # Reject a month that can only be drawn in part -- a grid with holes in it
    # is harder to explain than a refusal naming the supported window.
    if first_ad < MIN_AD_DATE or last_ad > MAX_AD_DATE:
        raise DateOutOfRangeError(
            f"AD {year}-{month:02d} is not fully inside the convertible window "
            f"{MIN_AD_DATE.isoformat()} through {MAX_AD_DATE.isoformat()}"
        )

    first_bs, last_bs = ad_to_bs(first_ad), ad_to_bs(last_ad)
    start = f"{BS_MONTH_NAMES[first_bs.month - 1]} {first_bs.day}"
    end = f"{BS_MONTH_NAMES[last_bs.month - 1]} {last_bs.day}"
    years = (
        str(first_bs.year) if first_bs.year == last_bs.year else f"{first_bs.year}/{last_bs.year}"
    )
    return MonthGrid(
        title=f"{calendar.month_name[month]} {year}",
        subtitle=f"{start} - {end}, {years}",
        weeks=_build_weeks(_sunday_first_index(first_ad), total_days),
    )


def render_body(grid: MonthGrid) -> str:
    """The weekday header and week rows, without the two heading lines."""
    rows = [
        " ".join(
            f"{day:>{_CELL_WIDTH}}" if day is not None else " " * _CELL_WIDTH for day in week
        ).rstrip()
        for week in grid.weeks
    ]
    return "\n".join([WEEKDAY_HEADER, *rows])


def render_plain(grid: MonthGrid) -> str:
    """The whole grid as plain text, centred over the week columns."""
    width = len(WEEKDAY_HEADER)
    return "\n".join(
        [grid.title.center(width).rstrip(), grid.subtitle.center(width).rstrip(), render_body(grid)]
    )
