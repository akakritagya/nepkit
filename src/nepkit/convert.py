"""Conversion between Bikram Sambat and Gregorian dates.

Both directions collapse to a day count from calendar_data.ANCHOR and expand
out the other side; the AD-side expander is datetime.date arithmetic.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Final

from nepkit.calendar_data import (
    ANCHOR,
    TOTAL_DAYS,
    bs_from_days,
    check_bs_date,
    days_from_anchor,
)
from nepkit.exceptions import DateOutOfRangeError, InvalidDateError

# Computed from ANCHOR plus the table's length, never written down as literals.
# ANCHOR.ad_date is the only AD fact in the package that cannot be derived (see
# data/DATA.md); a second AD literal here would be free to drift away from it.
MIN_AD_DATE: Final[date] = ANCHOR.ad_date
MAX_AD_DATE: Final[date] = ANCHOR.ad_date + timedelta(days=TOTAL_DAYS - 1)

_DATE_PARTS: Final[int] = 3


def _parse_ymd(text: str) -> tuple[int, int, int]:
    """Parse strict "YYYY-MM-DD" without regard to which calendar it belongs to.

    Shared by `BSDate.fromisoformat` and `nepkit.text.parse_ad_date`, so
    identical garbage produces an identical error either side of the
    calendar boundary.

    Parameters
    ----------
    text : str
        The date string to parse.

    Returns
    -------
    tuple of (int, int, int)
        The `(year, month, day)` parsed from `text`.

    Raises
    ------
    InvalidDateError
        If `text` is not in "YYYY-MM-DD" form.
    """
    parts = text.split("-")
    # isdecimal(), not isdigit(): isdigit() also accepts characters like "²"
    # that int() then rejects, which would raise ValueError here instead of
    # the InvalidDateError this function promises.
    if len(parts) != _DATE_PARTS or not all(part.isdecimal() for part in parts):
        raise InvalidDateError(f"{text!r} is not a date in YYYY-MM-DD form")
    year, month, day = (int(part) for part in parts)
    return year, month, day


@dataclass(frozen=True, slots=True)
class BSDate:
    """A Bikram Sambat date, validated on construction against the bundled table.

    Parameters
    ----------
    year : int
        The Bikram Sambat year.
    month : int
        The Bikram Sambat month, 1-12.
    day : int
        The day of the month.

    Raises
    ------
    InvalidDateError
        If `(year, month, day)` is not a real BS date.
    DateOutOfRangeError
        If `year` is outside the bundled table's range.
    """

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        """Validate the date against the bundled table."""
        check_bs_date(self.year, self.month, self.day)

    def isoformat(self) -> str:
        """Format as zero-padded "YYYY-MM-DD" -- the ISO 8601 *layout*, applied to a BS date.

        This is not an ISO 8601 date: `datetime.date.fromisoformat` will
        happily accept the result and return a different, wrong Gregorian
        day, with no error to signal the mistake. The string is only ever
        meaningful alongside something that says it is Bikram Sambat.

        Returns
        -------
        str
            The formatted date.
        """
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def __str__(self) -> str:
        """Alias for `isoformat`, the same relationship `date.__str__` has to it."""
        return self.isoformat()

    @classmethod
    def fromisoformat(cls, text: str) -> "BSDate":
        """Parse "YYYY-MM-DD" into a `BSDate`.

        Parameters
        ----------
        text : str
            The date string to parse.

        Returns
        -------
        BSDate
            The parsed and validated date.

        Raises
        ------
        InvalidDateError
            If `text` is not in "YYYY-MM-DD" form, or is not a real BS date.
        DateOutOfRangeError
            If the year is outside the bundled table's range.
        """
        year, month, day = _parse_ymd(text)
        return cls(year=year, month=month, day=day)


def bs_to_ad(bs: BSDate) -> date:
    """Convert a Bikram Sambat date to its Gregorian equivalent.

    Parameters
    ----------
    bs : BSDate
        The Bikram Sambat date to convert.

    Returns
    -------
    date
        The equivalent Gregorian date.
    """
    return ANCHOR.ad_date + timedelta(days=days_from_anchor(bs.year, bs.month, bs.day))


def ad_to_bs(ad: date) -> BSDate:
    """Convert a Gregorian date to its Bikram Sambat equivalent.

    Parameters
    ----------
    ad : date
        The Gregorian date to convert.

    Returns
    -------
    BSDate
        The equivalent Bikram Sambat date.

    Raises
    ------
    DateOutOfRangeError
        If `ad` is outside `[MIN_AD_DATE, MAX_AD_DATE]`.
    """
    if not (MIN_AD_DATE <= ad <= MAX_AD_DATE):
        raise DateOutOfRangeError(
            f"AD {ad.isoformat()} is outside the convertible window "
            f"{MIN_AD_DATE.isoformat()} through {MAX_AD_DATE.isoformat()}"
        )
    year, month, day = bs_from_days((ad - ANCHOR.ad_date).days)
    return BSDate(year=year, month=month, day=day)


@dataclass(frozen=True, slots=True)
class BSDateTime:
    """A Bikram Sambat date and time, in Nepal Standard Time (UTC+05:45).

    Composes a validated BSDate with a stdlib time-of-day rather than
    reinventing hour/minute/second/microsecond validation nepkit does not
    need to own. The civil BS calendar changes date at midnight NPT, the
    same convention any other civil calendar uses -- the sunrise-based day
    start belongs to the separate Hindu panchang/tithi system nepkit does
    not model. nepkit works only in NPT: see `bs_datetime_to_ad_datetime`
    and `ad_datetime_to_bs_datetime` for what that means for conversion.

    Parameters
    ----------
    date : BSDate
        The Bikram Sambat date.
    time : datetime.time, optional
        The time of day, in Nepal Standard Time. Default is midnight.
    """

    date: BSDate
    time: time = time()

    def isoformat(self, *, sep: str = "T") -> str:
        """Format as "YYYY-MM-DD[T ]HH:MM:SS[.ffffff]", the same shape `datetime.isoformat` uses.

        Parameters
        ----------
        sep : str, optional
            The character separating the date and time halves. Default is "T".

        Returns
        -------
        str
            The formatted date and time.
        """
        return f"{self.date.isoformat()}{sep}{self.time.isoformat()}"

    def __str__(self) -> str:
        """Alias for `isoformat`, the same relationship `datetime.__str__` has to it."""
        return self.isoformat(sep=" ")

    @classmethod
    def fromisoformat(cls, text: str) -> "BSDateTime":
        """Parse "YYYY-MM-DD[T ]HH:MM:SS[.ffffff]" into a `BSDateTime`.

        Parameters
        ----------
        text : str
            The date-time string to parse.

        Returns
        -------
        BSDateTime
            The parsed and validated date and time, in Nepal Standard Time.

        Raises
        ------
        InvalidDateError
            If `text` is not in the expected form, its time half carries
            tzinfo, or its date half is not a real BS date.
        DateOutOfRangeError
            If the year is outside the bundled table's range.
        """
        date_text, sep, time_text = text.partition("T")
        if not sep:
            date_text, sep, time_text = text.partition(" ")
        if not sep:
            raise InvalidDateError(f"{text!r} has no date/time separator ('T' or ' ')")
        try:
            clock = time.fromisoformat(time_text)
        except ValueError as exc:
            raise InvalidDateError(f"{time_text!r} is not a valid time of day") from exc
        # time.fromisoformat accepts a trailing offset ("14:32:07+05:45", "...Z")
        # and returns a tz-aware time -- silently keeping it would produce a
        # BSDateTime whose clock is not NPT, the same mistake
        # ad_datetime_to_bs_datetime already refuses for a tz-aware datetime.
        if clock.tzinfo is not None:
            raise InvalidDateError(
                f"{time_text!r} carries a UTC offset -- nepkit works only in Nepal "
                "Standard Time; pass a naive time"
            )
        return cls(date=BSDate.fromisoformat(date_text), time=clock)


def bs_datetime_to_ad_datetime(bdt: BSDateTime) -> datetime:
    """Convert a Bikram Sambat date and time to its Gregorian equivalent.

    Both calendars change date at the same midnight instant in Nepal
    Standard Time, so only the date half needs converting -- the time of
    day carries straight through unchanged.

    Parameters
    ----------
    bdt : BSDateTime
        The Bikram Sambat date and time to convert, in Nepal Standard Time.

    Returns
    -------
    datetime.datetime
        The equivalent Gregorian date and time, naive, in Nepal Standard
        Time.
    """
    return datetime.combine(bs_to_ad(bdt.date), bdt.time)


def ad_datetime_to_bs_datetime(adt: datetime) -> BSDateTime:
    """Convert a Gregorian date and time to its Bikram Sambat equivalent.

    Parameters
    ----------
    adt : datetime.datetime
        The Gregorian date and time to convert. Must be naive -- nepkit
        works only in Nepal Standard Time and does not convert between
        timezones. A tz-aware value should be converted to NPT with
        `astimezone` and stripped of its tzinfo before calling this.

    Returns
    -------
    BSDateTime
        The equivalent Bikram Sambat date and time, in Nepal Standard Time.

    Raises
    ------
    InvalidDateError
        If `adt` carries tzinfo. Silently treating a tz-aware value's clock
        digits as NPT would produce an answer that is quietly wrong by
        whatever the real offset is, rather than failing loudly the way
        every other malformed input to this package does.
    DateOutOfRangeError
        If `adt`'s date is outside `[MIN_AD_DATE, MAX_AD_DATE]`.
    """
    if adt.tzinfo is not None:
        raise InvalidDateError(
            f"{adt.isoformat()} carries tzinfo -- nepkit works only in Nepal "
            "Standard Time; convert to NPT and strip tzinfo before calling "
            "ad_datetime_to_bs_datetime"
        )
    return BSDateTime(date=ad_to_bs(adt.date()), time=adt.time())
