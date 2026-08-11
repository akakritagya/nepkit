"""nepkit — typed Bikram Sambat ↔ Gregorian date conversion.

Everything a caller needs is re-exported here, so the module layout underneath
stays free to change without breaking imports.
"""

from nepkit.calendar_data import MAX_BS_YEAR, MIN_BS_YEAR, days_in_month
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import (
    CalendarDataError,
    DateError,
    DateOutOfRangeError,
    InvalidDateError,
    NepkitError,
)

__all__ = [
    "MAX_AD_DATE",
    "MAX_BS_YEAR",
    "MIN_AD_DATE",
    "MIN_BS_YEAR",
    "BSDate",
    "CalendarDataError",
    "DateError",
    "DateOutOfRangeError",
    "InvalidDateError",
    "NepkitError",
    "ad_to_bs",
    "bs_to_ad",
    "days_in_month",
]
