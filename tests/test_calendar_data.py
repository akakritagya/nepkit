"""Tier 1: prove each calendar_data invariant rejects a deliberately bad row."""

import json
from datetime import date
from importlib import resources
from typing import Self

import pytest

from nepkit import calendar_data
from nepkit.calendar_data import (
    ANCHOR,
    MAX_BS_YEAR,
    MIN_BS_YEAR,
    TOTAL_DAYS,
    Anchor,
    BSYearData,
    _check_anchor_is_first_day_of_min_year,
    _check_contiguous,
    bs_from_days,
    days_from_anchor,
    days_in_month,
)
from nepkit.exceptions import CalendarDataError, DateOutOfRangeError, InvalidDateError


def test_wrong_month_count_is_rejected() -> None:
    with pytest.raises(CalendarDataError, match="expected 12 months, got 11"):
        BSYearData(year=2000, months=(30, 31, 30, 31, 30, 31, 30, 31, 30, 31, 30))


def test_month_length_too_low_is_rejected() -> None:
    # Sums to 365 and every other month is in range, so only the first month's
    # 28 days (below the 29 minimum) can be what trips this.
    months = (28, 32, 32, 32, 31, 31, 30, 30, 30, 30, 30, 29)
    with pytest.raises(CalendarDataError, match="month 1: 28 days is outside"):
        BSYearData(year=2000, months=months)


def test_month_length_too_high_is_rejected() -> None:
    # Sums to 365 and every other month is in range, so only the first month's
    # 33 days (above the 32 maximum) can be what trips this.
    months = (33, 30, 30, 30, 30, 30, 30, 30, 30, 30, 31, 31)
    with pytest.raises(CalendarDataError, match="month 1: 33 days is outside"):
        BSYearData(year=2000, months=months)


def test_year_total_out_of_range_is_rejected() -> None:
    with pytest.raises(CalendarDataError, match="year totals 348 days"):
        BSYearData(year=2000, months=(29,) * 12)  # sums to 348, no real BS year is that short


def test_contiguity_gap_is_rejected() -> None:
    valid_months = (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30)
    years = (
        BSYearData(year=2000, months=valid_months),
        BSYearData(year=2002, months=valid_months),  # 2001 is missing
    )
    with pytest.raises(CalendarDataError, match="gap"):
        _check_contiguous(years)


def test_contiguity_duplicate_is_rejected_as_duplicate_not_gap() -> None:
    valid_months = (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30)
    years = (
        BSYearData(year=2000, months=valid_months),
        BSYearData(year=2000, months=valid_months),  # duplicate row, not a gap
    )
    with pytest.raises(CalendarDataError, match="duplicate"):
        _check_contiguous(years)


# Not parametrized: the wrong-day case carries a comment explaining why a
# year-only check would miss it, and that's the whole point of this cluster —
# folding it into an `ids` list would bury the one comment worth reading.
def test_anchor_year_mismatch_is_rejected() -> None:
    bad_year = MIN_BS_YEAR + 1
    bad_anchor = Anchor(bs_year=bad_year, bs_month=1, bs_day=1, ad_date=date(1943, 4, 14))
    with pytest.raises(CalendarDataError, match=f"{bad_year}-01-01 is not the first day"):
        _check_anchor_is_first_day_of_min_year(bad_anchor, MIN_BS_YEAR)


def test_anchor_matching_year_but_wrong_day_is_rejected() -> None:
    # Year matches, so a year-only check would miss this: every offset built from
    # this anchor would be silently short by two days.
    bad_anchor = Anchor(bs_year=MIN_BS_YEAR, bs_month=1, bs_day=3, ad_date=date(1943, 4, 14))
    with pytest.raises(CalendarDataError, match=f"{MIN_BS_YEAR}-01-03 is not the first day"):
        _check_anchor_is_first_day_of_min_year(bad_anchor, MIN_BS_YEAR)


def test_anchor_matching_year_but_wrong_month_is_rejected() -> None:
    bad_anchor = Anchor(bs_year=MIN_BS_YEAR, bs_month=5, bs_day=1, ad_date=date(1943, 4, 14))
    with pytest.raises(CalendarDataError, match=f"{MIN_BS_YEAR}-05-01 is not the first day"):
        _check_anchor_is_first_day_of_min_year(bad_anchor, MIN_BS_YEAR)


def test_bundled_range_matches_expected_bounds() -> None:
    assert MIN_BS_YEAR == 2000
    assert MAX_BS_YEAR == 2090


def test_days_in_month_returns_bundled_value() -> None:
    assert days_in_month(2000, 1) == 30
    assert days_in_month(2090, 12) == 30


@pytest.mark.parametrize(
    ("year", "month", "exc", "match"),
    [
        (MIN_BS_YEAR - 1, 1, DateOutOfRangeError, "outside the bundled range"),
        (MAX_BS_YEAR + 1, 1, DateOutOfRangeError, "outside the bundled range"),
        (MIN_BS_YEAR, 0, InvalidDateError, r"outside \[1, 12\]"),
        (MIN_BS_YEAR, 13, InvalidDateError, r"outside \[1, 12\]"),
    ],
    ids=["year_below", "year_above", "month_zero", "month_thirteen"],
)
def test_days_in_month_rejects_bad_input(
    year: int, month: int, exc: type[Exception], match: str
) -> None:
    with pytest.raises(exc, match=match):
        days_in_month(year, month)


def test_days_from_anchor_is_zero_at_the_anchor() -> None:
    assert days_from_anchor(ANCHOR.bs_year, ANCHOR.bs_month, ANCHOR.bs_day) == 0


def test_days_from_anchor_accumulates_across_a_year_boundary() -> None:
    # BS 2000's months sum to 365, so BS 2001-01-01 is 365 days from the anchor.
    assert days_from_anchor(2001, 1, 1) == 365


@pytest.mark.parametrize(
    ("year", "month", "day", "match"),
    [
        (2000, 1, 31, r"outside \[1, 30\]"),  # BS 2000 month 1 has only 30 days
        (MIN_BS_YEAR, 1, 0, r"outside \[1,"),
    ],
    ids=["day_past_month_end", "day_zero"],
)
def test_days_from_anchor_rejects_bad_day(year: int, month: int, day: int, match: str) -> None:
    with pytest.raises(InvalidDateError, match=match):
        days_from_anchor(year, month, day)


def test_bs_from_days_returns_the_anchor_at_zero() -> None:
    assert bs_from_days(0) == (ANCHOR.bs_year, ANCHOR.bs_month, ANCHOR.bs_day)


def test_bs_from_days_walks_months_within_a_year() -> None:
    # BS 2000 month 1 has 30 days, so day 30 is the first day of month 2.
    assert bs_from_days(30) == (2000, 2, 1)


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (365, (2001, 1, 1)),  # BS 2000 sums to 365, so this is the next year's first day
        (TOTAL_DAYS - 1, (MAX_BS_YEAR, 12, 30)),  # the very last representable day
    ],
    ids=["first_year_boundary", "last_representable_day"],
)
def test_bs_from_days_crosses_year_boundaries(days: int, expected: tuple[int, int, int]) -> None:
    assert bs_from_days(days) == expected


@pytest.mark.parametrize(
    "days",
    # Unguarded, a negative count bisects to index -1 and walks the *last* year
    # backwards, returning something like (2090, 1, -32873) with no error at all.
    # That silent wrong answer is what this guard exists to turn into a raise.
    [-1, TOTAL_DAYS],
    ids=["before_anchor", "past_last_day"],
)
def test_bs_from_days_rejects_days_outside_the_bundled_span(days: int) -> None:
    with pytest.raises(DateOutOfRangeError, match=r"outside \[0, 33238\)"):
        bs_from_days(days)


class _StubResource:
    """Stands in for the importlib.resources.files(...).joinpath(...) chain."""

    def __init__(self, text: str) -> None:
        self._text = text

    def joinpath(self, name: str) -> Self:
        assert name == "calendar.json"
        return self

    def read_text(self, *, encoding: str) -> str:
        return self._text


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ("not json", "is not valid JSON"),
        ({}, "non-empty list"),
        ([], "non-empty list"),
        ([{"year": 2000}], "malformed"),
        ([{"year": 2000, "months": "not-a-list"}], "malformed"),
        ([{"year": "2000", "months": [30] * 12}], "malformed"),
        ([{"year": 2000, "months": [30] * 11 + ["x"]}], "malformed"),
        # These two clear every _load_years parsing check — valid JSON, a list, a
        # dict with both keys, year an int, months a list of ints — so only
        # BSYearData.__post_init__ can reject them. If the loader ever starts
        # building something other than a real BSYearData, these are what catch it.
        ([{"year": 2000, "months": [30] * 11}], "expected 12 months, got 11"),
        ([{"year": 2000, "months": [29] * 12}], "year totals 348 days"),
    ],
    ids=[
        "invalid_json_syntax",
        "not_a_list",
        "empty_list",
        "row_missing_months",
        "months_not_a_list",
        "year_not_int",
        "month_not_int",
        "row_fails_month_count_invariant",
        "row_fails_year_total_invariant",
    ],
)
def test_load_years_rejects_bad_calendar_json(
    monkeypatch: pytest.MonkeyPatch, payload: object, match: str
) -> None:
    raw_json = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(resources, "files", lambda package: _StubResource(raw_json))
    with pytest.raises(CalendarDataError, match=match):
        calendar_data._load_years()
