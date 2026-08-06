class NepkitError(Exception):
    """Base for every error nepkit raises."""


class CalendarDataError(NepkitError):
    """The bundled calendar table is malformed. Raised at import."""


class DateError(NepkitError):
    """Base for date-input problems."""


class InvalidDateError(DateError):
    """Syntactically parseable, but not a real BS date."""


class DateOutOfRangeError(DateError):
    """Outside the range the bundled table covers."""
