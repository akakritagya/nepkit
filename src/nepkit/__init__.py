"""nepkit — typed Bikram Sambat ↔ Gregorian date conversion.

Everything a caller needs is re-exported here, so the module layout underneath
stays free to change without breaking imports.
"""

from importlib.metadata import version

from nepkit.calendar_data import (
    BS_MONTH_NAMES,
    BS_MONTH_NAMES_NE,
    MAX_BS_YEAR,
    MIN_BS_YEAR,
    days_in_month,
)
from nepkit.convert import (
    MAX_AD_DATE,
    MIN_AD_DATE,
    BSDate,
    BSDateTime,
    ad_datetime_to_bs_datetime,
    ad_to_bs,
    bs_datetime_to_ad_datetime,
    bs_to_ad,
)
from nepkit.exceptions import (
    CalendarDataError,
    DateError,
    DateOutOfRangeError,
    InvalidDateError,
    NepkitError,
)
from nepkit.text import (
    bs_month_name,
    format_ad_date,
    format_bs_date,
    parse_ad_date,
    parse_ad_month,
    parse_bs_date,
    parse_bs_month,
    to_devnagari_numerals,
    weekday_name,
)

# Read from the installed package's metadata rather than duplicated here, so
# pyproject.toml's `version` stays the one place it can drift out of sync.
__version__: str = version("nepkit")

__all__ = [
    "BS_MONTH_NAMES",
    "BS_MONTH_NAMES_NE",
    "MAX_AD_DATE",
    "MAX_BS_YEAR",
    "MIN_AD_DATE",
    "MIN_BS_YEAR",
    "BSDate",
    "BSDateTime",
    "CalendarDataError",
    "DateError",
    "DateOutOfRangeError",
    "InvalidDateError",
    "NepkitError",
    "__version__",
    "ad_datetime_to_bs_datetime",
    "ad_to_bs",
    "bs_datetime_to_ad_datetime",
    "bs_month_name",
    "bs_to_ad",
    "days_in_month",
    "format_ad_date",
    "format_bs_date",
    "parse_ad_date",
    "parse_ad_month",
    "parse_bs_date",
    "parse_bs_month",
    "to_devnagari_numerals",
    "weekday_name",
]
