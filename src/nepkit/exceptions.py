"""Nepkit's exception hierarchy.

Every error nepkit raises descends from `NepkitError`, split into two
branches: a malformed bundled calendar table (`CalendarDataError`, raised at
import) and a bad date input (`DateError`, raised at call time), further
split into `InvalidDateError` and `DateOutOfRangeError`.
"""


class NepkitError(Exception):
    """Base class for every error nepkit raises."""


class CalendarDataError(NepkitError):
    """Raised when the bundled calendar table is malformed.

    Raised at import time, since the table is loaded and validated as soon
    as `nepkit.calendar_data` is imported.
    """


class DateError(NepkitError):
    """Base class for date-input problems."""


class InvalidDateError(DateError):
    """Raised when a date is syntactically parseable but not a real BS date.

    For example, BS month 13, or day 33 in a 32-day month.
    """


class DateOutOfRangeError(DateError):
    """Raised when a date is real but outside the bundled table's range."""
