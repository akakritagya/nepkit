"""The surface `import nepkit` exposes, and the example the README promises.

Pinning __all__ exactly means adding or removing a public name has to be a
deliberate edit to this list, not a side effect of touching a module.
"""

from datetime import date
from importlib.metadata import version

import nepkit
from nepkit import BSDate, ad_to_bs, bs_to_ad

EXPECTED_PUBLIC_API = {
    "BSDate",
    "BSDateTime",
    "bs_to_ad",
    "ad_to_bs",
    "bs_datetime_to_ad_datetime",
    "ad_datetime_to_bs_datetime",
    "days_in_month",
    "BS_MONTH_NAMES",
    "BS_MONTH_NAMES_NE",
    "MIN_BS_YEAR",
    "MAX_BS_YEAR",
    "MIN_AD_DATE",
    "MAX_AD_DATE",
    "NepkitError",
    "CalendarDataError",
    "DateError",
    "InvalidDateError",
    "DateOutOfRangeError",
    "__version__",
    "parse_bs_date",
    "parse_ad_date",
    "format_bs_date",
    "format_ad_date",
    "parse_bs_month",
    "parse_ad_month",
    "bs_month_name",
    "weekday_name",
    "to_devnagari_numerals",
}


def test_package_exports_exactly_the_documented_public_api() -> None:
    assert set(nepkit.__all__) == EXPECTED_PUBLIC_API


def test_every_exported_name_actually_resolves() -> None:
    missing = [name for name in nepkit.__all__ if not hasattr(nepkit, name)]
    assert not missing, f"listed in __all__ but not importable: {missing}"


def test_dunder_version_matches_the_installed_package_metadata() -> None:
    assert nepkit.__version__ == version("nepkit")


def test_the_readme_usage_example_works() -> None:
    # If this breaks, the README is lying to a stranger following it verbatim.
    assert bs_to_ad(BSDate(year=2081, month=4, day=15)) == date(2024, 7, 30)
    assert ad_to_bs(date(2024, 7, 30)) == BSDate(year=2081, month=4, day=15)


def test_the_readme_library_text_example_works() -> None:
    assert str(nepkit.BSDate(2081, 4, 15)) == "2081-04-15"
    assert nepkit.BSDate.fromisoformat("2081-04-15") == BSDate(year=2081, month=4, day=15)
    assert nepkit.parse_bs_date("15 Baishakh 2081") == BSDate(year=2081, month=1, day=15)
    assert nepkit.format_bs_date(BSDate(2081, 4, 15), named=True) == "15 Shrawan 2081"
    assert nepkit.parse_ad_date("30 Jul 2024") == date(2024, 7, 30)
