"""nepkit — typed Bikram Sambat ↔ Gregorian date conversion.

Everything a caller needs is re-exported here, so the module layout underneath
stays free to change without breaking imports.
"""

from importlib.metadata import version

from nepkit.calendar_data import BS_MONTH_NAMES, MAX_BS_YEAR, MIN_BS_YEAR, days_in_month
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import (
    CalendarDataError,
    DateError,
    DateOutOfRangeError,
    InvalidDateError,
    NepkitError,
)

# Read from the installed package's metadata rather than duplicated here, so
# pyproject.toml's `version` stays the one place it can drift out of sync.
__version__: str = version("nepkit")

__all__ = [
    "BS_MONTH_NAMES",
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
    "__version__",
    "ad_to_bs",
    "bs_to_ad",
    "days_in_month",
]
