"""BS <-> AD conversion: the anchor arithmetic and the errors it raises."""

from datetime import date

import pytest

from nepkit.calendar_data import ANCHOR, MAX_BS_YEAR, TOTAL_DAYS
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import DateOutOfRangeError, InvalidDateError


def test_bsdate_keeps_the_fields_it_was_given() -> None:
    bs = BSDate(year=2081, month=4, day=15)
    assert (bs.year, bs.month, bs.day) == (2081, 4, 15)


def test_bsdate_rejects_a_day_past_the_end_of_its_month() -> None:
    # BS 2000 month 1 has 30 days, so the 31st does not exist.
    with pytest.raises(InvalidDateError, match=r"outside \[1, 30\]"):
        BSDate(year=2000, month=1, day=31)


def test_bsdate_rejects_a_year_the_table_does_not_cover() -> None:
    with pytest.raises(DateOutOfRangeError, match="outside the bundled range"):
        BSDate(year=MAX_BS_YEAR + 1, month=1, day=1)


def test_bs_to_ad_returns_the_anchor_ad_date_at_the_anchor() -> None:
    anchor = BSDate(year=ANCHOR.bs_year, month=ANCHOR.bs_month, day=ANCHOR.bs_day)
    assert bs_to_ad(anchor) == ANCHOR.ad_date


def test_bs_to_ad_crosses_a_year_boundary() -> None:
    # BS 2000 is 365 days long. AD 1943-04-14 + 365 lands on 1944-04-13, one short
    # of the Gregorian anniversary, because 1944 is a leap year and Feb 29 is inside
    # the span. Hardcoded rather than computed so this can disagree with the code.
    assert bs_to_ad(BSDate(year=2001, month=1, day=1)) == date(1944, 4, 13)


def test_bs_to_ad_at_the_last_representable_date() -> None:
    assert bs_to_ad(BSDate(year=MAX_BS_YEAR, month=12, day=30)) == date(2034, 4, 13)


@pytest.mark.parametrize(
    ("ad", "expected"),
    [
        (date(1943, 4, 14), BSDate(year=2000, month=1, day=1)),
        (date(1944, 4, 13), BSDate(year=2001, month=1, day=1)),
        (date(2034, 4, 13), BSDate(year=2090, month=12, day=30)),
    ],
    ids=["anchor", "first_year_boundary", "last_representable_day"],
)
def test_ad_to_bs_converts_known_pairs(ad: date, expected: BSDate) -> None:
    assert ad_to_bs(ad) == expected


@pytest.mark.parametrize(
    "ad",
    [date(1943, 4, 13), date(2034, 4, 14)],
    ids=["day_before_window", "day_after_window"],
)
def test_ad_to_bs_rejects_dates_outside_the_convertible_window(ad: date) -> None:
    # Without a guard here the error *type* is already right, because bs_from_days
    # raises DateOutOfRangeError. But its message talks about day counts and BS
    # years, which is unusable to a caller holding an AD date. The window has to be
    # stated in the units the caller is working in.
    with pytest.raises(DateOutOfRangeError, match="1943-04-14 through 2034-04-13"):
        ad_to_bs(ad)


def test_ad_window_is_derived_from_the_table() -> None:
    # The second assertion is the one that matters: it pins the window's width to
    # the table's length, so extending calendar.json has to move both ends together.
    assert (date(1943, 4, 14), date(2034, 4, 13)) == (MIN_AD_DATE, MAX_AD_DATE)
    assert (MAX_AD_DATE - MIN_AD_DATE).days + 1 == TOTAL_DAYS
