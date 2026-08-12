"""Month-grid construction and plain-text rendering, with no CLI involved.

These are pure functions on purpose: the layout logic is the part most likely
to be wrong, and it should be testable without a CliRunner or a terminal.
"""

from datetime import date, timedelta

import pytest

from nepkit.calendar_data import BS_MONTH_NAMES
from nepkit.convert import BSDate
from nepkit.exceptions import DateOutOfRangeError, InvalidDateError
from nepkit.render import (
    ACCENT,
    TODAY_STYLE,
    WEEKDAY_ABBREVIATIONS,
    WEEKDAY_HEADER,
    ad_month_grid,
    bs_month_grid,
    render_body,
    render_body_markup,
    render_plain,
    weekday_name,
)


def test_there_are_twelve_bs_month_names_in_calendar_order() -> None:
    assert len(BS_MONTH_NAMES) == 12
    assert BS_MONTH_NAMES[0] == "Baisakh"
    assert BS_MONTH_NAMES[3] == "Shrawan"
    assert BS_MONTH_NAMES[11] == "Chaitra"


def test_bs_month_grid_lays_out_shrawan_2081() -> None:
    # BS 2081-04-01 = AD 2024-07-16, a Tuesday, and the month has 32 days.
    # Sunday-first, so Tuesday leaves two blank cells before the 1st.
    grid = bs_month_grid(2081, 4)
    assert grid.title == "Shrawan 2081"
    assert grid.subtitle == "16 Jul - 16 Aug 2024"
    assert grid.weeks[0] == (None, None, 1, 2, 3, 4, 5)
    assert grid.weeks[1] == (6, 7, 8, 9, 10, 11, 12)
    assert grid.weeks[-1] == (27, 28, 29, 30, 31, 32, None)
    assert len(grid.weeks) == 5


def test_ad_month_grid_lays_out_july_2024() -> None:
    # 1 July 2024 is a Monday, so Sunday-first leaves one blank cell.
    grid = ad_month_grid(2024, 7)
    assert grid.title == "July 2024"
    assert grid.weeks[0] == (None, 1, 2, 3, 4, 5, 6)
    assert grid.weeks[-1] == (28, 29, 30, 31, None, None, None)


def test_ad_month_grid_subtitle_names_both_bs_months_it_spans() -> None:
    # An AD month never lines up with a BS month: July 2024 runs from
    # Ashadh 17 to Shrawan 16, so a single month name would be a lie.
    assert ad_month_grid(2024, 7).subtitle == "Ashadh 17 - Shrawan 16, 2081"


def test_every_grid_row_has_exactly_seven_cells() -> None:
    for grid in (bs_month_grid(2081, 4), ad_month_grid(2024, 7)):
        assert all(len(week) == 7 for week in grid.weeks)


def test_render_plain_centres_the_headings_over_the_week_columns() -> None:
    rendered = render_plain(bs_month_grid(2081, 4)).splitlines()
    assert rendered[0].strip() == "Shrawan 2081"
    assert rendered[1].strip() == "16 Jul - 16 Aug 2024"
    assert rendered[2] == WEEKDAY_HEADER
    assert rendered[3] == "          1   2   3   4   5"
    assert rendered[4] == "  6   7   8   9  10  11  12"
    assert all(len(line) <= len(WEEKDAY_HEADER) for line in rendered)


def test_a_subtitle_wider_than_the_grid_centres_the_grid_under_it() -> None:
    """AD 2026-04 spans 'Chaitra 18 - Baisakh 17, 2082/2083' -- 34 columns to the
    grid's 27. The block is as wide as the subtitle, so the grid has to move to
    the middle of it instead of hugging the left edge.
    """
    grid = ad_month_grid(2026, 4)
    assert len(grid.subtitle) > len(WEEKDAY_HEADER), "this month no longer exercises the case"

    lines = render_plain(grid).splitlines()
    block = max(len(line) for line in lines)
    header = next(line for line in lines if line.lstrip().startswith("Sun"))
    left = len(header) - len(header.lstrip())
    right = block - len(header)
    assert left > 0, "the grid was not shifted at all"
    assert abs(left - right) <= 1, f"grid is off centre: {left} left, {right} right"


def test_a_grid_wider_than_its_subtitle_is_not_shifted() -> None:
    """Shrawan 2081's span is 20 columns, well inside the grid, so nothing moves."""
    lines = render_plain(bs_month_grid(2081, 4)).splitlines()
    header = next(line for line in lines if line.lstrip().startswith("Sun"))
    assert header == WEEKDAY_HEADER


def test_centring_moves_the_whole_grid_together() -> None:
    """Every row shifts by the same amount, or the weekday columns stop lining up."""
    body = render_body(ad_month_grid(2026, 4)).splitlines()
    pad = len(body[0]) - len(body[0].lstrip())
    for row in body[1:]:
        assert row.startswith(" " * pad), f"row does not share the header's indent: {row!r}"


def test_render_plain_emits_no_ansi_escapes() -> None:
    assert "\x1b[" not in render_plain(ad_month_grid(2024, 7))


def test_a_grid_marks_today_when_today_falls_inside_it() -> None:
    grid = bs_month_grid(2081, 4, today=BSDate(2081, 4, 15))
    assert grid.today == 15


@pytest.mark.parametrize(
    "today",
    [BSDate(2081, 5, 1), BSDate(2081, 3, 30), BSDate(2080, 4, 15), None],
    ids=["next_month", "previous_month", "same_month_other_year", "not_supplied"],
)
def test_a_grid_marks_nothing_when_today_falls_elsewhere(today: BSDate | None) -> None:
    assert bs_month_grid(2081, 4, today=today).today is None


def test_ad_grid_marks_today_too() -> None:
    assert ad_month_grid(2024, 7, today=date(2024, 7, 4)).today == 4
    assert ad_month_grid(2024, 7, today=date(2024, 8, 4)).today is None


def test_render_body_markup_styles_only_todays_cell() -> None:
    grid = bs_month_grid(2081, 4, today=BSDate(2081, 4, 15))
    body = render_body_markup(grid)
    # The padding is inside the span, which is harmless for a foreground style
    # and keeps cell construction uniform. Markup adds no printed width, so
    # column alignment is unaffected either way.
    assert f"[{TODAY_STYLE}] 15[/]" in body
    assert f"[{TODAY_STYLE}] 14[/]" not in body
    assert body.count(f"[{TODAY_STYLE}]") == 1


def test_render_body_markup_is_unstyled_when_today_is_absent() -> None:
    body = render_body_markup(bs_month_grid(2081, 4))
    assert TODAY_STYLE not in body
    assert body == render_body(bs_month_grid(2081, 4))


def test_plain_rendering_is_byte_identical_whether_or_not_today_is_known() -> None:
    """Piped output must not change shape just because the clock moved.

    Anything parsing stdout would break on a marker appearing for one day a
    month, so the highlight lives only in the markup path.
    """
    with_today = render_plain(bs_month_grid(2081, 4, today=BSDate(2081, 4, 15)))
    without = render_plain(bs_month_grid(2081, 4))
    assert with_today == without


@pytest.mark.parametrize(
    ("year", "month"),
    [(2081, 13), (2081, 0)],
    ids=["month_thirteen", "month_zero"],
)
def test_bs_month_grid_rejects_an_impossible_month(year: int, month: int) -> None:
    with pytest.raises(InvalidDateError):
        bs_month_grid(year, month)


def test_bs_month_grid_rejects_a_year_outside_the_table() -> None:
    with pytest.raises(DateOutOfRangeError):
        bs_month_grid(2095, 1)


@pytest.mark.parametrize(
    ("year", "month"),
    # April 1943 is only convertible from the 14th, and April 2034 only to the
    # 13th, so neither month can be drawn in full. Rejecting a partial month is
    # simpler to explain than silently drawing one with holes in it.
    [(1943, 4), (2034, 4), (1900, 1)],
    ids=["first_partial_month", "last_partial_month", "far_outside"],
)
def test_ad_month_grid_rejects_a_month_it_cannot_fully_convert(year: int, month: int) -> None:
    with pytest.raises(DateOutOfRangeError):
        ad_month_grid(year, month)


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2024, 7, 28), "Sun"),
        (date(2024, 7, 29), "Mon"),
        (date(2024, 7, 30), "Tue"),
        (date(2024, 7, 31), "Wed"),
        (date(2024, 8, 1), "Thu"),
        (date(2024, 8, 2), "Fri"),
        (date(2024, 8, 3), "Sat"),
    ],
)
def test_weekday_name_covers_a_whole_week(day: date, expected: str) -> None:
    """One known week, so an off-by-one in the Sunday-first shift cannot hide."""
    assert weekday_name(day) == expected


def test_weekday_abbreviations_are_the_grid_header() -> None:
    """The abbreviation and the column it sits under must never disagree.

    Deriving one from the other is what makes that structural rather than a
    thing to remember, so this pins the derivation itself.
    """
    assert tuple(WEEKDAY_HEADER.split()) == WEEKDAY_ABBREVIATIONS
    assert len(WEEKDAY_ABBREVIATIONS) == 7


def test_weekday_name_agrees_with_the_column_a_day_lands_in() -> None:
    """Cross-check against the grid: the name must match the printed column.

    bs_month_grid already places days in Sunday-first columns, so walking a
    rendered week and reading its header proves weekday_name and the layout
    share one notion of which day is which.
    """
    grid = bs_month_grid(2081, 4)
    body_rows = render_body(grid).splitlines()
    header_columns = body_rows[0].split()
    first_ad = date(2024, 7, 16)  # BS 2081-04-01
    for offset in range(7):
        day = first_ad + timedelta(days=offset)
        column = header_columns[(day.weekday() + 1) % 7]
        assert weekday_name(day) == column


def test_todays_highlight_is_the_bright_form_of_the_panel_accent() -> None:
    """The highlight is meant to match the calendar box, not merely resemble it.

    Deriving TODAY_STYLE from ACCENT is what stops the two drifting apart when
    someone recolours one of them, so the derivation is the thing worth pinning.
    """
    assert f"bold bright_{ACCENT}" == TODAY_STYLE
    assert ACCENT in TODAY_STYLE
