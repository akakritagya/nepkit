"""Tier 1: prove each calendar_data invariant rejects a deliberately bad row."""

from datetime import date

import pytest

from nepkit.calendar_data import (
    ANCHOR,
    MAX_BS_YEAR,
    MIN_BS_YEAR,
    Anchor,
    BSYearData,
    _check_anchor_is_first_day_of_min_year,
    _check_contiguous,
    days_from_anchor,
    days_in_month,
)
from nepkit.exceptions import CalendarDataError, DateOutOfRangeError, InvalidDateError


def test_wrong_month_count_is_rejected() -> None:
    with pytest.raises(CalendarDataError):
        BSYearData(year=2000, months=(30, 31, 30, 31, 30, 31, 30, 31, 30, 31, 30))


def test_month_length_too_low_is_rejected() -> None:
    with pytest.raises(CalendarDataError):
        BSYearData(year=2000, months=(28, 31, 30, 31, 30, 31, 30, 31, 30, 31, 30, 31))


def test_month_length_too_high_is_rejected() -> None:
    with pytest.raises(CalendarDataError):
        BSYearData(year=2000, months=(33, 31, 30, 31, 30, 31, 30, 31, 30, 31, 30, 31))


def test_year_total_out_of_range_is_rejected() -> None:
    with pytest.raises(CalendarDataError):
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


def test_anchor_year_mismatch_is_rejected() -> None:
    bad_anchor = Anchor(bs_year=2001, bs_month=1, bs_day=1, ad_date=date(1943, 4, 14))
    with pytest.raises(CalendarDataError):
        _check_anchor_is_first_day_of_min_year(bad_anchor, 2000)


def test_anchor_matching_year_but_wrong_day_is_rejected() -> None:
    # Year matches, so a year-only check would miss this: every offset built from
    # this anchor would be silently short by two days.
    bad_anchor = Anchor(bs_year=2000, bs_month=1, bs_day=3, ad_date=date(1943, 4, 14))
    with pytest.raises(CalendarDataError):
        _check_anchor_is_first_day_of_min_year(bad_anchor, 2000)


def test_anchor_matching_year_but_wrong_month_is_rejected() -> None:
    bad_anchor = Anchor(bs_year=2000, bs_month=5, bs_day=1, ad_date=date(1943, 4, 14))
    with pytest.raises(CalendarDataError):
        _check_anchor_is_first_day_of_min_year(bad_anchor, 2000)


def test_bundled_range_matches_expected_bounds() -> None:
    assert MIN_BS_YEAR == 2000
    assert MAX_BS_YEAR == 2090


def test_days_in_month_returns_bundled_value() -> None:
    assert days_in_month(2000, 1) == 30
    assert days_in_month(2090, 12) == 30


def test_days_in_month_rejects_year_below_range() -> None:
    with pytest.raises(DateOutOfRangeError):
        days_in_month(MIN_BS_YEAR - 1, 1)


def test_days_in_month_rejects_year_above_range() -> None:
    with pytest.raises(DateOutOfRangeError):
        days_in_month(MAX_BS_YEAR + 1, 1)


def test_days_in_month_rejects_month_zero() -> None:
    with pytest.raises(InvalidDateError):
        days_in_month(MIN_BS_YEAR, 0)


def test_days_in_month_rejects_month_thirteen() -> None:
    with pytest.raises(InvalidDateError):
        days_in_month(MIN_BS_YEAR, 13)


def test_days_from_anchor_is_zero_at_the_anchor() -> None:
    assert days_from_anchor(ANCHOR.bs_year, ANCHOR.bs_month, ANCHOR.bs_day) == 0


def test_days_from_anchor_accumulates_across_a_year_boundary() -> None:
    # BS 2000's months sum to 365, so BS 2001-01-01 is 365 days from the anchor.
    assert days_from_anchor(2001, 1, 1) == 365


def test_days_from_anchor_rejects_day_past_month_end() -> None:
    with pytest.raises(InvalidDateError):
        days_from_anchor(2000, 1, 31)  # BS 2000 month 1 has only 30 days


def test_days_from_anchor_rejects_day_zero() -> None:
    with pytest.raises(InvalidDateError):
        days_from_anchor(MIN_BS_YEAR, 1, 0)
