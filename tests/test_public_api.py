"""The surface `import nepkit` exposes, and the example the README promises.

Pinning __all__ exactly means adding or removing a public name has to be a
deliberate edit to this list, not a side effect of touching a module.
"""

from datetime import date

import nepkit
from nepkit import BSDate, ad_to_bs, bs_to_ad

EXPECTED_PUBLIC_API = {
    "BSDate",
    "bs_to_ad",
    "ad_to_bs",
    "days_in_month",
    "BS_MONTH_NAMES",
    "MIN_BS_YEAR",
    "MAX_BS_YEAR",
    "MIN_AD_DATE",
    "MAX_AD_DATE",
    "NepkitError",
    "CalendarDataError",
    "DateError",
    "InvalidDateError",
    "DateOutOfRangeError",
}


def test_package_exports_exactly_the_documented_public_api() -> None:
    assert set(nepkit.__all__) == EXPECTED_PUBLIC_API


def test_every_exported_name_actually_resolves() -> None:
    missing = [name for name in nepkit.__all__ if not hasattr(nepkit, name)]
    assert not missing, f"listed in __all__ but not importable: {missing}"


def test_the_readme_usage_example_works() -> None:
    # If this breaks, the README is lying to a stranger following it verbatim.
    assert bs_to_ad(BSDate(year=2081, month=4, day=15)) == date(2024, 7, 30)
    assert ad_to_bs(date(2024, 7, 30)) == BSDate(year=2081, month=4, day=15)
