"""Month-grid construction and plain-text rendering.

Pure functions: no I/O, no terminal detection, no CLI framework. The CLI layer
decides where output goes and whether to dress it up; everything about *what*
the grid contains is decided and tested here.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from rich.cells import cell_len

from nepkit.calendar_data import days_in_month
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import DateOutOfRangeError
from nepkit.text import (
    AD_MONTH_ABBREVIATIONS,
    AD_MONTH_NAMES,
    WEEKDAY_ABBREVIATIONS,
    WEEKDAY_ABBREVIATIONS_NE,
    bs_month_name,
    to_devnagari_numerals,
)

_DAYS_PER_WEEK: Final[int] = 7
_CELL_WIDTH: Final[int] = 3
# Devnagari vowel signs, virama, and anusvara are extra code points that render
# narrower than 1 terminal column each (some contribute none at all) -- Python's
# len() cannot see that, so width here is measured with rich's cell_len, the
# same measurement rich.Panel itself uses, or Devnagari mode's box borders
# drift from its own content by a column or two. Comes out to 3 either way for
# the current abbreviations, same as Latin, but stays derived rather than
# assumed in case the set ever changes.
_DEVNAGARI_CELL_WIDTH: Final[int] = max(
    _CELL_WIDTH, *(cell_len(name) for name in WEEKDAY_ABBREVIATIONS_NE)
)


def _pad_left(text: str, width: int) -> str:
    """Right-align `text` to `width` terminal columns.

    Not Python's `f"{text:>{width}}"`: that pads by code-point count, and
    Devnagari text's terminal width does not always match its code-point
    count (see `_DEVNAGARI_CELL_WIDTH`). `width` is assumed to already be at
    least `cell_len(text)`; a `text` wider than `width` is returned unpadded.

    Parameters
    ----------
    text : str
        The text to pad.
    width : int
        The target width, in terminal columns.

    Returns
    -------
    str
        `text`, preceded by enough spaces to fill `width` columns.
    """
    return " " * max(0, width - cell_len(text)) + text


def _center(text: str, width: int) -> str:
    """Centre `text` within `width` terminal columns, trailing padding stripped.

    Not `text.center(width).rstrip()`: `str.center` measures by code-point
    count, which disagrees with terminal-column width for Devnagari text
    (see `_pad_left`). This replicates `str.center`'s own left/right split
    -- `margin // 2`, plus one extra column on the left when both the
    margin and the target width are odd -- rather than a plain `margin //
    2`, which was tried first here and silently shifted every centred
    Latin title by a column versus what `str.center` had always produced,
    caught only by re-diffing DEMO.md's captured output against a live run
    after the fact. Only the leading half matters: the trailing half gets
    stripped right back off by every caller.

    Parameters
    ----------
    text : str
        The text to centre.
    width : int
        The target width, in terminal columns.

    Returns
    -------
    str
        `text`, preceded by the padding `str.center(width)` would put
        before it.
    """
    margin = max(0, width - cell_len(text))
    return " " * (margin // 2 + (margin & width & 1)) + text


def _header_row(abbreviations: tuple[str, ...], *, width: int) -> str:
    """Right-align each of `abbreviations` to `width` and join with single spaces.

    Parameters
    ----------
    abbreviations : tuple of str
        The 7 weekday abbreviations, Sunday first.
    width : int
        The column width to pad each one to.

    Returns
    -------
    str
        The header line.
    """
    return " ".join(_pad_left(name, width) for name in abbreviations)


WEEKDAY_HEADER: Final[str] = _header_row(WEEKDAY_ABBREVIATIONS, width=_CELL_WIDTH)
"""The Latin header, `"Sun Mon Tue Wed Thu Fri Sat"`. Devnagari mode builds its
own, wider one at render time -- see `_header_row`."""

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


def bs_month_grid(
    year: int, month: int, *, today: BSDate | None = None, devnagari: bool = False
) -> MonthGrid:
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
    devnagari : bool, optional
        Render the title's month name in Devnagari, and every numeral in
        both the title and subtitle as Devnagari digits -- including the
        subtitle's Gregorian day and year, since that is a numeral-system
        choice, not a claim about which calendar the number belongs to. The
        subtitle's Gregorian month abbreviation (e.g. "Jul") is untouched
        either way: nepkit has no Devnagari names for the Gregorian
        calendar to substitute. Default is False.

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

    title = f"{bs_month_name(month, devnagari=devnagari)} {year}"
    start = f"{first_ad.day:02d} {AD_MONTH_ABBREVIATIONS[first_ad.month - 1]}"
    end = f"{last_ad.day:02d} {AD_MONTH_ABBREVIATIONS[last_ad.month - 1]} {last_ad.year}"
    span = f"{start} - {end}"
    if devnagari:
        title, span = to_devnagari_numerals(title), to_devnagari_numerals(span)
    marked = today.day if today is not None and (today.year, today.month) == (year, month) else None
    return MonthGrid(
        title=title,
        subtitle=span,
        weeks=_build_weeks(_sunday_first_index(first_ad), total_days),
        today=marked,
    )


def ad_month_grid(
    year: int, month: int, *, today: date | None = None, devnagari: bool = False
) -> MonthGrid:
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
    devnagari : bool, optional
        Render the subtitle's BS month names in Devnagari, and every
        numeral in the title and subtitle -- BS and Gregorian alike -- as
        Devnagari digits. The title's Gregorian month name (e.g. "July")
        is untouched either way, same reasoning as `bs_month_grid`.
        Default is False.

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
    start = f"{bs_month_name(first_bs.month, devnagari=devnagari)} {first_bs.day}"
    end = f"{bs_month_name(last_bs.month, devnagari=devnagari)} {last_bs.day}"
    years = (
        str(first_bs.year) if first_bs.year == last_bs.year else f"{first_bs.year}/{last_bs.year}"
    )
    title = f"{AD_MONTH_NAMES[month - 1]} {year}"
    subtitle = f"{start} - {end}, {years}"
    if devnagari:
        title, subtitle = to_devnagari_numerals(title), to_devnagari_numerals(subtitle)
    marked = today.day if today is not None and (today.year, today.month) == (year, month) else None
    return MonthGrid(
        title=title,
        subtitle=subtitle,
        weeks=_build_weeks(_sunday_first_index(first_ad), total_days),
        today=marked,
    )


def _active_header(*, devnagari: bool) -> tuple[str, int]:
    """Pick the weekday header text and column width for the requested script.

    Parameters
    ----------
    devnagari : bool
        Whether to use WEEKDAY_ABBREVIATIONS_NE at `_DEVNAGARI_CELL_WIDTH`
        instead of WEEKDAY_ABBREVIATIONS at `_CELL_WIDTH`.

    Returns
    -------
    tuple of (str, int)
        The header line, and the column width every cell in the body must
        also use to stay aligned under it.
    """
    if devnagari:
        header = _header_row(WEEKDAY_ABBREVIATIONS_NE, width=_DEVNAGARI_CELL_WIDTH)
        return header, _DEVNAGARI_CELL_WIDTH
    return WEEKDAY_HEADER, _CELL_WIDTH


def _cell(day: int | None, *, width: int, devnagari: bool) -> str:
    """Format one grid cell.

    Parameters
    ----------
    day : int or None
        The day number, or None for a blank cell.
    width : int
        The column width to pad to -- from `_active_header`, so a cell
        always matches the header it renders under.
    devnagari : bool
        Whether to render the day number with Devnagari digits.

    Returns
    -------
    str
        The day right-aligned to `width`, or that many spaces.
    """
    if day is None:
        return " " * width
    text = to_devnagari_numerals(str(day)) if devnagari else str(day)
    return _pad_left(text, width)


def block_width(grid: MonthGrid, *, devnagari: bool = False) -> int:
    """Compute how wide the rendered block is.

    Parameters
    ----------
    grid : MonthGrid
        The grid to measure.
    devnagari : bool, optional
        Whether the Devnagari weekday header (wider than the Latin one)
        will be rendered alongside this grid. Default is False.

    Returns
    -------
    int
        The grid's width, unless a heading is wider.
    """
    header, _ = _active_header(devnagari=devnagari)
    return max(cell_len(header), cell_len(grid.title), cell_len(grid.subtitle))


def _indent(grid: MonthGrid, *, devnagari: bool = False) -> str:
    """Compute the left pad that centres the week columns under a wider heading.

    Applied identically to every row, including the weekday header, so the
    columns stay in step however far the block has to shift.

    Parameters
    ----------
    grid : MonthGrid
        The grid being rendered.
    devnagari : bool, optional
        Whether the Devnagari weekday header is in use. Default is False.

    Returns
    -------
    str
        The left-padding spaces.
    """
    header, _ = _active_header(devnagari=devnagari)
    width = block_width(grid, devnagari=devnagari)
    return " " * (max(0, width - cell_len(header)) // 2)


def _rows(grid: MonthGrid, *, mark_today: bool, devnagari: bool = False) -> list[str]:
    """Render each week of `grid` as one padded, space-joined line.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.
    mark_today : bool
        Whether to wrap today's cell in rich markup.
    devnagari : bool, optional
        Whether to render day numbers with Devnagari digits. Default is
        False.

    Returns
    -------
    list of str
        One line per week.
    """
    _, width = _active_header(devnagari=devnagari)
    pad = _indent(grid, devnagari=devnagari)
    rows: list[str] = []
    for week in grid.weeks:
        cells = [
            f"[{TODAY_STYLE}]{_cell(day, width=width, devnagari=devnagari)}[/]"
            if mark_today and day is not None and day == grid.today
            else _cell(day, width=width, devnagari=devnagari)
            for day in week
        ]
        rows.append((pad + " ".join(cells)).rstrip())
    return rows


def render_body(grid: MonthGrid, *, devnagari: bool = False) -> str:
    """Render the weekday header and week rows as plain text with no markup at all.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.
    devnagari : bool, optional
        Render the weekday header and day numbers in Devnagari. Default is
        False.

    Returns
    -------
    str
        The header and week rows, newline-joined.
    """
    header, _ = _active_header(devnagari=devnagari)
    rows = _rows(grid, mark_today=False, devnagari=devnagari)
    return "\n".join([_indent(grid, devnagari=devnagari) + header, *rows])


def render_body_markup(grid: MonthGrid, *, devnagari: bool = False) -> str:
    """Render the same grid as render_body, with today's cell wrapped in rich markup.

    Kept separate from render_body so the plain path cannot accidentally grow
    escape sequences: anything piping stdout depends on it staying inert.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.
    devnagari : bool, optional
        Render the weekday header and day numbers in Devnagari. Default is
        False.

    Returns
    -------
    str
        The header and week rows, with today's cell marked up.
    """
    header, _ = _active_header(devnagari=devnagari)
    rows = _rows(grid, mark_today=True, devnagari=devnagari)
    return "\n".join([_indent(grid, devnagari=devnagari) + header, *rows])


def render_plain(grid: MonthGrid, *, devnagari: bool = False) -> str:
    """Render the whole grid as plain text, every part centred on the same block.

    Parameters
    ----------
    grid : MonthGrid
        The grid to render.
    devnagari : bool, optional
        Render the weekday header and day numbers in Devnagari. The
        title and subtitle are unaffected here -- they are already in
        their final script, decided when the grid was built. Default is
        False.

    Returns
    -------
    str
        The title, subtitle, and body, newline-joined.
    """
    width = block_width(grid, devnagari=devnagari)
    return "\n".join(
        [
            _center(grid.title, width),
            _center(grid.subtitle, width),
            render_body(grid, devnagari=devnagari),
        ]
    )
