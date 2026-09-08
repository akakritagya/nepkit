"""The exception hierarchy, and why InvalidDateError/DateOutOfRangeError are split.

Run: uv run python demo/03_error_handling.py

    NepkitError
    +-- CalendarDataError   the bundled table is malformed; raised at import,
    |                       so it never shows up here -- nothing below
    |                       triggers it deliberately
    +-- DateError
        +-- InvalidDateError      not a real BS date (month 13, day 33, ...)
        +-- DateOutOfRangeError   a real date, but outside the bundled range
"""

import _bootstrap  # noqa: F401 -- inserts ../src onto sys.path as a side effect

from nepkit import BSDate, DateError, DateOutOfRangeError, InvalidDateError

# BS month 13 doesn't exist -- syntactically a date shape, but not a real one.
try:
    BSDate(2081, 13, 1)
except InvalidDateError as exc:
    print(f"BSDate(2081, 13, 1) -> InvalidDateError: {exc}")

# Shrawan (BS month 4) has 32 days in 2081; day 33 overshoots it.
try:
    BSDate(2081, 4, 33)
except InvalidDateError as exc:
    print(f"BSDate(2081, 4, 33) -> InvalidDateError: {exc}")

# BS 2095-01-01 is a perfectly real date -- nepkit just has no data for it.
# The bundled table only covers BS 2000 through 2090.
try:
    BSDate(2095, 1, 1)
except DateOutOfRangeError as exc:
    print(f"BSDate(2095, 1, 1) -> DateOutOfRangeError: {exc}")

# Catching each type separately lets a caller react differently: a real date
# outside the range is worth retrying against another source; an invalid one
# never is. A caller who wants one except clause instead of two can catch the
# shared DateError base and still branch on the concrete type it caught.
for year, month, day in [(2081, 13, 1), (2081, 4, 33), (2095, 1, 1)]:
    try:
        BSDate(year, month, day)
    except DateError as exc:
        if isinstance(exc, DateOutOfRangeError):
            print(f"BS {year}-{month:02d}-{day:02d}: real date, out of range, retry elsewhere")
        else:
            print(f"BS {year}-{month:02d}-{day:02d}: not a real date, don't retry")
