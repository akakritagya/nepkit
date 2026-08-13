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
WEEKDAY_ABBREVIATIONS: Final[tuple[str, ...]] = tuple(WEEKDAY_HEADER.split())
"""The header's columns, reused as names. Derived so the two cannot disagree."""

_DAYS_PER_WEEK: Final[int] = 7
_CELL_WIDTH: Final[int] = 3

ACCENT: Final[str] = "cyan"
"""The calendar panel's border colour, which the CLI imports rather than repeats.

Today's highlight below is the bright form of this same hue, so recolouring the
calendar moves both together instead of leaving two literals to drift apart.
Must stay one of rich's eight base colour names, since that derivation assumes
a `bright_` counterpart exists.
"""

# Colours the digits themselves rather than filling the cell background, so the
# grid keeps an even texture and today reads as one bright number in it.
TODAY_STYLE: Final[str] = f"bold bright_{ACCENT}"


@dataclass(frozen=True, slots=True)
class MonthGrid:
    """One month laid out as Sunday-first weeks, plus its two heading lines.

    Parameters
    ----------
    title : str
        The month and year, e.g. "Shrawan 2081".
    subtitle : str
        The span this month covers in the other calendar.
    weeks : tuple of tuple of (int or None)
        Each week as 7 cells, Sunday first. A cell is None where the month
        has no day, either before day 1 or after the last day.
    today : int or None, optional
        Day of this month to highlight, or None when today falls outside it.
        Default is None.
    """

    title: str
    subtitle: str
    weeks: tuple[tuple[int | None, ...], ...]
    today: int | None = None


def _sunday_first_index(day: date) -> int:
    """Map a Gregorian date to its Sunday-first weekday index.

    Python weeks start Monday; Nepali (and `cal`) calendars start Sunday.

    Parameters
    ----------
    day : date
        The date to index.

    Returns
    -------
    int
        0 for Sunday through 6 for Saturday.
    """
    return (day.weekday() + 1) % _DAYS_PER_WEEK


def weekday_name(day: date) -> str:
    """Look up the Sunday-first weekday abbreviation for a Gregorian date.

    Deliberately not strftime("%a"), which is locale-dependent: under
    LC_TIME=fr_FR that yields "mer." while the grid header still says "Wed".
    Reading the name out of WEEKDAY_HEADER means the abbreviation and the column
    it sits under can never disagree, and the output is byte-identical on every
    machine -- which DEMO.md's captured blocks rely on, and CI now checks on
    three platforms.

    Parameters
    ----------
    day : date
        The date to name.

    Returns
    -------
    str
        A three-letter abbreviation, e.g. "Wed".
    """
    return WEEKDAY_ABBREVIATIONS[_sunday_first_index(day)]


def _build_weeks(lead_blanks: int, total_days: int) -> tuple[tuple[int | None, ...], ...]:
    """Lay `total_days` numbered cells into Sunday-first weeks.

    Parameters
    ----------
    lead_blanks : int
        Empty cells before day 1, i.e. the Sunday-first index of day 1.
    total_days : int
        The number of days in the month.

    Returns
    -------
    tuple of tuple of (int or None)
        Each week as 7 cells; None marks a cell outside the month.
    """
    cells: list[int | None] = [None] * lead_blanks + list(range(1, total_days + 1))
    while len(cells) % _DAYS_PER_WEEK:
        cells.append(None)
    return tuple(
        tuple(cells[start : start + _DAYS_PER_WEEK])
        for start in range(0, len(cells), _DAYS_PER_WEEK)
    )


def bs_month_grid(year: int, month: int, *, today: BSDate | None = None) -> MonthGrid:
    """Lay out a Bikram Sambat month, cross-referenced to the Gregorian dates it spans.

    `today` is passed in rather than read from the clock so this stays pure and
    the caller keeps one seam for the current date.

    Parameters
    ----------
    year : int
        The Bikram Sambat year.
    month : int
        The Bikram Sambat month, 1-12.
    today : BSDate or None, optional
        The current BS date, used to mark today's cell if it falls inside
        this month. Default is None.

    Returns
    -------
    MonthGrid
        The laid-out month.

    Raises
    ------
    InvalidDateError
        If `month` is not `1-12`.
    DateOutOfRangeError
        If `year` is outside the bundled table's range.
    """
    first_bs = BSDate(year=year, month=month, day=1)  # validates year and month
    total_days = days_in_month(year, month)
    first_ad = bs_to_ad(first_bs)
    last_ad = first_ad + timedelta(days=total_days - 1)

    span = f"{first_ad.strftime('%d %b')} - {last_ad.strftime('%d %b %Y')}"
    marked = today.day if today is not None and (today.year, today.month) == (year, month) else None
    return MonthGrid(
        title=f"{BS_MONTH_NAMES[month - 1]} {year}",
        subtitle=span,
        weeks=_build_weeks(_sunday_first_index(first_ad), total_days),
        today=marked,
    )


def ad_month_grid(year: int, month: int, *, today: date | None = None) -> MonthGrid:
    """Lay out a Gregorian month, cross-referenced to the BS months it spans.

    A Gregorian month never lines up with a BS month, so the subtitle names
    both ends rather than pretending there is a single corresponding month.

    Parameters
    ----------
    year : int
        The Gregorian year.
    month : int
        The Gregorian month, 1-12.
    today : date or None, optional
        The current Gregorian date, used to mark today's cell if it falls
        inside this month. Default is None.

    Returns
    -------
    MonthGrid
        The laid-out month.

    Raises
    ------
    DateOutOfRangeError
        If `month` is not `1-12`, or if the month is not fully inside the
        convertible AD window.
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
    marked = today.day if today is not None and (today.year, today.month) == (year, month) else None
    return MonthGrid(
        title=f"{calendar.month_name[month]} {year}",
        subtitle=f"{start} - {end}, {years}",
        weeks=_build_weeks(_sunday_first_index(first_ad), total_days),
        today=marked,
    )


def _cell(day: int | None) -> str:
    """Format one grid cell.

    Parameters
    ----------
    day : int or None
        The day number, or None for a blank cell.

    Returns
    -------
    str
        The day right-aligned to `_CELL_WIDTH`, or that many spaces.
    """
    return f"{day:>{_CELL_WIDTH}}" if day is not None else " " * _CELL_WIDTH


def block_width(grid: MonthGrid) -> int:
    """Compute how wide the rendered block is.

    Parameters
    ----------
    grid : MonthGrid
        The grid to measure.

    Returns
    -------
    int
        The grid's width, unless a heading is wider.
    """
    return max(len(WEEKDAY_HEADER), len(grid.title), len(grid.subtitle))


def _indent(grid: MonthGrid) -> str:
    """Compute the left pad that centres the week columns under a wider heading.

    Applied identically to every row, including the weekday header, so the
    columns stay in step however far the block has to shift.

    Parameters
    ----------
    grid : MonthGrid
        The grid being rendered.

    Returns
    -------
    str
        The left-padding spaces.
    """
    return " " * ((block_width(grid) - len(WEEKDAY_HEADER)) // 2)


def _rows(grid: MonthGrid, *, mark_today: bool) -> list[str]:
    """Render each week of `grid` as one padded, space-joined line.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.
    mark_today : bool
        Whether to wrap today's cell in rich markup.

    Returns
    -------
    list of str
        One line per week.
    """
    pad = _indent(grid)
    rows: list[str] = []
    for week in grid.weeks:
        cells = [
            f"[{TODAY_STYLE}]{_cell(day)}[/]"
            if mark_today and day is not None and day == grid.today
            else _cell(day)
            for day in week
        ]
        rows.append((pad + " ".join(cells)).rstrip())
    return rows


def render_body(grid: MonthGrid) -> str:
    """Render the weekday header and week rows as plain text with no markup at all.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.

    Returns
    -------
    str
        The header and week rows, newline-joined.
    """
    return "\n".join([_indent(grid) + WEEKDAY_HEADER, *_rows(grid, mark_today=False)])


def render_body_markup(grid: MonthGrid) -> str:
    """Render the same grid as render_body, with today's cell wrapped in rich markup.

    Kept separate from render_body so the plain path cannot accidentally grow
    escape sequences: anything piping stdout depends on it staying inert.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.

    Returns
    -------
    str
        The header and week rows, with today's cell marked up.
    """
    return "\n".join([_indent(grid) + WEEKDAY_HEADER, *_rows(grid, mark_today=True)])


def render_plain(grid: MonthGrid) -> str:
    """Render the whole grid as plain text, every part centred on the same block.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.

    Returns
    -------
    str
        The title, subtitle, and body, newline-joined.
    """
    width = block_width(grid)
    return "\n".join(
        [grid.title.center(width).rstrip(), grid.subtitle.center(width).rstrip(), render_body(grid)]
    )
