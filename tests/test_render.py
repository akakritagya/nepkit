"""Month-grid construction and plain-text rendering, with no CLI involved.

These are pure functions on purpose: the layout logic is the part most likely
to be wrong, and it should be testable without a CliRunner or a terminal.
"""

import pytest

from nepkit.calendar_data import BS_MONTH_NAMES
from nepkit.exceptions import DateOutOfRangeError, InvalidDateError
from nepkit.render import WEEKDAY_HEADER, ad_month_grid, bs_month_grid, render_plain


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


def test_render_plain_emits_no_ansi_escapes() -> None:
    assert "\x1b[" not in render_plain(ad_month_grid(2024, 7))


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
