"""BSDateTime and the two datetime conversion functions -- and their NPT-only limit.

Run: uv run python demo/04_datetime_conversion.py
"""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import _bootstrap  # noqa: F401 -- inserts ../src onto sys.path as a side effect

from nepkit import (
    BSDate,
    BSDateTime,
    InvalidDateError,
    ad_datetime_to_bs_datetime,
    bs_datetime_to_ad_datetime,
)

# BSDateTime composes a validated BSDate with a plain time of day, in Nepal
# Standard Time (UTC+05:45) -- nepkit does not convert between timezones.
bdt = BSDateTime(date=BSDate(2081, 4, 15), time=time(14, 32))
print(f"Constructed: {bdt}")

# Both calendars change date at the same midnight instant in NPT, so only the
# date half needs converting -- the time of day carries straight through.
adt = bs_datetime_to_ad_datetime(bdt)
print(f"bs_datetime_to_ad_datetime({bdt}) -> {adt}")

back = ad_datetime_to_bs_datetime(adt)
print(f"ad_datetime_to_bs_datetime({adt}) -> {back}")
print(f"Round trip matches original: {back == bdt}")

# A tz-aware datetime is rejected outright rather than silently treated as
# NPT -- silently keeping a UTC offset would produce a BSDateTime whose clock
# is quietly wrong by however far off NPT that offset is.
aware = datetime(2024, 7, 30, 14, 32, tzinfo=UTC)
try:
    ad_datetime_to_bs_datetime(aware)
except InvalidDateError as exc:
    print(f"ad_datetime_to_bs_datetime(<UTC-aware datetime>) -> InvalidDateError: {exc}")

# The fix is to convert to NPT and strip tzinfo yourself before calling in --
# nepkit refuses to guess which timezone a naive value would have meant.
naive_npt = aware.astimezone(ZoneInfo("Asia/Kathmandu")).replace(tzinfo=None)
print(f"14:32 UTC converted to NPT and stripped -> {ad_datetime_to_bs_datetime(naive_npt)}")
