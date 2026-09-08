"""Core round trip: BSDate construction, bs_to_ad/ad_to_bs, days_in_month, range.

Run: uv run python demo/01_basic_conversion.py
"""

from datetime import date

import _bootstrap  # noqa: F401 -- inserts ../src onto sys.path as a side effect

from nepkit import (
    MAX_AD_DATE,
    MAX_BS_YEAR,
    MIN_AD_DATE,
    MIN_BS_YEAR,
    BSDate,
    __version__,
    ad_to_bs,
    bs_to_ad,
    days_in_month,
)

print(f"nepkit {__version__}")

# BSDate validates itself against the bundled table the moment it's built --
# if you're holding one, it's a real, in-range Bikram Sambat date.
bs = BSDate(2081, 4, 15)
print(f"Constructed: {bs}")

# Both directions collapse to a day count from a single verified anchor date,
# so a round trip always lands back where it started.
ad = bs_to_ad(bs)
print(f"bs_to_ad({bs}) -> {ad}")

back = ad_to_bs(ad)
print(f"ad_to_bs({ad}) -> {back}")
print(f"Round trip matches original: {back == bs}")

# ad_to_bs takes a datetime.date, so a malformed Gregorian date can't even
# reach nepkit -- Python's own date() constructor rejects it first.
print(f"ad_to_bs(date(2024, 7, 30)) -> {ad_to_bs(date(2024, 7, 30))}")

# Gregorian leap years follow a rule you can write down; BS month lengths
# don't. They're fixed by observation and range from 29 to 32 days with no
# generating formula -- this is why nepkit ships a lookup table instead of
# computing lengths.
print(f"days_in_month(2081, 4) -> {days_in_month(2081, 4)} days (Shrawan)")
print(f"days_in_month(2081, 9) -> {days_in_month(2081, 9)} days (Poush)")

# The supported range is computed from the bundled table, not written down
# separately -- extending the table would move these automatically. Both
# calendars' bounds derive from the same table plus the one verified anchor
# date, so the BS and AD windows always agree about which 33,238 days are
# covered.
print(f"Supported BS years: {MIN_BS_YEAR}..{MAX_BS_YEAR}")
print(f"Supported AD range: {MIN_AD_DATE}..{MAX_AD_DATE}")
