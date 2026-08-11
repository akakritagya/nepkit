"""Conversion between Bikram Sambat and Gregorian dates.

Both directions collapse to a day count from calendar_data.ANCHOR and expand
out the other side; the AD-side expander is datetime.date arithmetic.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from nepkit.calendar_data import (
    ANCHOR,
    TOTAL_DAYS,
    bs_from_days,
    check_bs_date,
    days_from_anchor,
)
from nepkit.exceptions import DateOutOfRangeError

# Computed from ANCHOR plus the table's length, never written down as literals.
# ANCHOR.ad_date is the only AD fact in the package that cannot be derived (see
# data/DATA.md); a second AD literal here would be free to drift away from it.
MIN_AD_DATE: Final[date] = ANCHOR.ad_date
MAX_AD_DATE: Final[date] = ANCHOR.ad_date + timedelta(days=TOTAL_DAYS - 1)


@dataclass(frozen=True, slots=True)
class BSDate:
    """A Bikram Sambat date, validated on construction against the bundled table."""

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        check_bs_date(self.year, self.month, self.day)


def bs_to_ad(bs: BSDate) -> date:
    """Convert a Bikram Sambat date to its Gregorian equivalent."""
    return ANCHOR.ad_date + timedelta(days=days_from_anchor(bs.year, bs.month, bs.day))


def ad_to_bs(ad: date) -> BSDate:
    """Convert a Gregorian date to its Bikram Sambat equivalent."""
    if not (MIN_AD_DATE <= ad <= MAX_AD_DATE):
        raise DateOutOfRangeError(
            f"AD {ad.isoformat()} is outside the convertible window "
            f"{MIN_AD_DATE.isoformat()} through {MAX_AD_DATE.isoformat()}"
        )
    year, month, day = bs_from_days((ad - ANCHOR.ad_date).days)
    return BSDate(year=year, month=month, day=day)
