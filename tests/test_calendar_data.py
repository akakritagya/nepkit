"""Tier 1: prove each calendar_data invariant rejects a deliberately bad row."""

import pytest

from nepkit.calendar_data import BSYearData, _check_contiguous
from nepkit.exceptions import CalendarDataError


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
    with pytest.raises(CalendarDataError):
        _check_contiguous(years)
