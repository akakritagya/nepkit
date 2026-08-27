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
