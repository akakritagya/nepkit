"""Date <-> human text: parsing, formatting, month names, weekday names, Devnagari digits.

Pure functions, no I/O. Sits below `render.py` (which needs month and weekday
names for grid titles) and above `convert.py` (which these functions parse
from and format to) -- `calendar_data <- convert <- text <- render <- cli`.
"""

from collections.abc import Mapping
from datetime import date
from typing import Final

from nepkit.calendar_data import BS_MONTH_ALIASES, BS_MONTH_NAMES, BS_MONTH_NAMES_NE
from nepkit.convert import BSDate, _parse_ymd
from nepkit.exceptions import CalendarDataError, InvalidDateError

WEEKDAY_ABBREVIATIONS: Final[tuple[str, ...]] = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
# Each name drops the shared "-बार" suffix (Sunday: आइतबार -> आइत), the same move
# BS_MONTH_NAMES_NE makes picking one spelling out of several real ones.
WEEKDAY_ABBREVIATIONS_NE: Final[tuple[str, ...]] = (
    "आइत",
    "सोम",
    "मंगल",
    "बुध",
    "बिही",
    "शुक्र",
    "शनि",
)

_DAYS_PER_WEEK: Final[int] = 7

# Deliberately not calendar.month_name / calendar.month_abbr / strftime("%b"):
# those read the current LC_TIME on every access (calendar._localized_month
# calls strftime freshly each time, uncached), so a caller who sets a French
# locale would get "juillet"/"juil." out of a package whose weekday names
# above are pinned English -- and the parse lookup built from them at import
# would stop matching the very output built from them at call time. Same
# argument weekday_name already makes against strftime("%a"), extended to
# months, which earlier code missed.
AD_MONTH_NAMES: Final[tuple[str, ...]] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
AD_MONTH_ABBREVIATIONS: Final[tuple[str, ...]] = tuple(name[:3] for name in AD_MONTH_NAMES)

_DEVNAGARI_DIGITS: Final[str] = "०१२३४५६७८९"
_TO_DEVNAGARI_DIGITS: Final[dict[int, int]] = str.maketrans("0123456789", _DEVNAGARI_DIGITS)


def to_devnagari_numerals(text: str) -> str:
    """Translate every ASCII digit in `text` to its Devnagari counterpart.

    Parameters
    ----------
    text : str
        Text that may contain ASCII digits 0-9. Non-digit characters, and any
        digit already in another script, pass through unchanged.

    Returns
    -------
    str
        `text` with every ASCII digit 0-9 replaced by its Devnagari form.
    """
    return text.translate(_TO_DEVNAGARI_DIGITS)


def bs_month_name(month: int, *, devnagari: bool = False) -> str:
    """Look up BS month `month`'s name in the requested script.

    Parameters
    ----------
    month : int
        The Bikram Sambat month, 1-12.
    devnagari : bool, optional
        Whether to use BS_MONTH_NAMES_NE instead of BS_MONTH_NAMES. Default
        is False.

    Returns
    -------
    str
        The month's name.
    """
    names = BS_MONTH_NAMES_NE if devnagari else BS_MONTH_NAMES
    return names[month - 1]


def weekday_name(day: date, *, devnagari: bool = False) -> str:
    """Look up the Sunday-first weekday abbreviation for a Gregorian date.

    Deliberately not strftime("%a"), which is locale-dependent: under
    LC_TIME=fr_FR that yields "mer." while the grid header still says "Wed".
    Reading the name out of a fixed tuple means the abbreviation and the column
    it sits under can never disagree, and the output is byte-identical on every
    machine -- which DEMO.md's captured blocks rely on, and CI now checks on
    three platforms.

    Parameters
    ----------
    day : date
        The date to name.
    devnagari : bool, optional
        Whether to use WEEKDAY_ABBREVIATIONS_NE instead of
        WEEKDAY_ABBREVIATIONS. Default is False.

    Returns
    -------
    str
        A weekday abbreviation, e.g. "Wed" or "बुध".
    """
    names = WEEKDAY_ABBREVIATIONS_NE if devnagari else WEEKDAY_ABBREVIATIONS
    # Python's date.weekday() is Monday-first (0=Mon); Nepali (and `cal`)
    # calendars start Sunday, hence the +1 rotation.
    return names[(day.weekday() + 1) % _DAYS_PER_WEEK]


def _build_bs_month_lookup() -> Mapping[str, int]:
    """Flatten BS_MONTH_NAMES, BS_MONTH_NAMES_NE, and BS_MONTH_ALIASES into one lookup.

    Refuses any alias claimed by two different months -- the same "malformed
    bundled data" treatment `calendar_data`'s own table loading gives a bad
    row, since a colliding alias is exactly that: bad data shipped with the
    package, not a bad call from a caller.

    Returns
    -------
    Mapping of str to int
        Casefolded month name or alias mapped to its 1-12 number.

    Raises
    ------
    CalendarDataError
        If an alias is claimed by two different months.
    """
    lookup: dict[str, int] = {}
    for number, name in enumerate(BS_MONTH_NAMES, start=1):
        lookup[name.casefold()] = number
    for number, name in enumerate(BS_MONTH_NAMES_NE, start=1):
        lookup[name] = number  # Devnagari has no case to fold.
    for number, aliases in enumerate(BS_MONTH_ALIASES, start=1):
        for alias in aliases:
            claimed = lookup.setdefault(alias, number)
            if claimed != number:
                raise CalendarDataError(
                    f"BS month alias {alias!r} maps to both month {claimed} and {number}"
                )
    return lookup


_BS_MONTH_LOOKUP: Final[Mapping[str, int]] = _build_bs_month_lookup()
_AD_MONTH_LOOKUP: Final[Mapping[str, int]] = {
    name.casefold(): number for number, name in enumerate(AD_MONTH_NAMES, start=1)
} | {abbr.casefold(): number for number, abbr in enumerate(AD_MONTH_ABBREVIATIONS, start=1)}

_DATE_PARTS: Final[int] = 3


def _parse_named_ymd(text: str, month_lookup: Mapping[str, int]) -> tuple[int, int, int] | None:
    """Parse "D Month YYYY", the month matched case-insensitively against `month_lookup`.

    Parameters
    ----------
    text : str
        The date string to parse.
    month_lookup : Mapping of str to int
        Casefolded month name/alias mapped to its 1-12 number.

    Returns
    -------
    tuple of (int, int, int) or None
        The `(year, month, day)` parsed from `text`, or None if `text` does
        not even have the "word word word" shape -- the caller falls back to
        the numeric form in that case instead of raising.

    Raises
    ------
    InvalidDateError
        If `text` has that shape but its month word is not recognised.
    """
    parts = text.split()
    # isdecimal(), not isdigit(): see _parse_ymd's matching note.
    if len(parts) != _DATE_PARTS or not parts[0].isdecimal() or not parts[2].isdecimal():
        return None
    day_text, month_text, year_text = parts
    month = month_lookup.get(month_text.casefold())
    if month is None:
        raise InvalidDateError(f"{month_text!r} is not a recognised month name")
    return int(year_text), month, int(day_text)


def parse_bs_month(text: str) -> int:
    """Parse a BS month as a number 1-12 or a name matched case-insensitively.

    Accepts a Devnagari name, or a Latin spelling from `BS_MONTH_NAMES` or a
    common variant of it. Range (1-12) is not checked here -- `BSDate` and
    the grid functions already validate that, and duplicating it here would
    just be two places that could disagree.

    Parameters
    ----------
    text : str
        The month, as a number or a name.

    Returns
    -------
    int
        The parsed month number.

    Raises
    ------
    InvalidDateError
        If `text` is neither a plain number nor a recognised month name.
    """
    if text.isdecimal():
        return int(text)
    month = _BS_MONTH_LOOKUP.get(text.casefold())
    if month is None:
        raise InvalidDateError(f"{text!r} is not a recognised month name")
    return month


def parse_ad_month(text: str) -> int:
    """Parse a Gregorian month as a number 1-12, a name, or its 3-letter abbreviation.

    Matched case-insensitively against `AD_MONTH_NAMES`/`AD_MONTH_ABBREVIATIONS`,
    never against the current locale -- see the note above `AD_MONTH_NAMES`.

    Parameters
    ----------
    text : str
        The month, as a number, name, or abbreviation.

    Returns
    -------
    int
        The parsed month number.

    Raises
    ------
    InvalidDateError
        If `text` is neither a plain number nor a recognised month name.
    """
    if text.isdecimal():
        return int(text)
    month = _AD_MONTH_LOOKUP.get(text.casefold())
    if month is None:
        raise InvalidDateError(f"{text!r} is not a recognised month name")
    return month


def parse_bs_date(text: str) -> BSDate:
    """Parse a Bikram Sambat date string.

    Parameters
    ----------
    text : str
        The date, as "YYYY-MM-DD" or "D Month YYYY" (e.g. "1 Baisakh 2083" or
        "1 बैशाख 2083"), the month matched case-insensitively.

    Returns
    -------
    BSDate
        The parsed and validated BS date.

    Raises
    ------
    InvalidDateError
        If `text` is not a real BS date.
    DateOutOfRangeError
        If the year is outside the bundled table's range.
    """
    if "-" in text:
        return BSDate.fromisoformat(text)
    named = _parse_named_ymd(text, _BS_MONTH_LOOKUP)
    if named is None:
        raise InvalidDateError(f"{text!r} is not a date in 'YYYY-MM-DD' or 'D Month YYYY' form")
    year, month, day = named
    return BSDate(year=year, month=month, day=day)


def parse_ad_date(text: str) -> date:
    """Parse a Gregorian date string.

    Parameters
    ----------
    text : str
        The date, as "YYYY-MM-DD" or "D Month YYYY" (e.g. "1 Jan 2000"), the
        month matched case-insensitively against either the full English
        name or its 3-letter abbreviation.

    Returns
    -------
    date
        The parsed Gregorian date.

    Raises
    ------
    InvalidDateError
        If `text` is not a real Gregorian date.
    """
    if "-" in text:
        year, month, day = _parse_ymd(text)
    else:
        named = _parse_named_ymd(text, _AD_MONTH_LOOKUP)
        if named is None:
            raise InvalidDateError(f"{text!r} is not a date in 'YYYY-MM-DD' or 'D Month YYYY' form")
        year, month, day = named
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise InvalidDateError(f"AD {text} is not a real Gregorian date") from exc


def format_bs_date(bs: BSDate, *, named: bool = False, devnagari: bool = False) -> str:
    """Format a BS date as "2081-04-15", or "15 Shrawan 2081" when `named`.

    Parameters
    ----------
    bs : BSDate
        The date to format.
    named : bool, optional
        Render as "day month year" instead of the zero-padded ISO layout.
        Default is False.
    devnagari : bool, optional
        Render the digits in Devnagari, and -- when `named` too -- the
        month name. Default is False.

    Returns
    -------
    str
        The formatted date.
    """
    if named:
        text = f"{bs.day} {bs_month_name(bs.month, devnagari=devnagari)} {bs.year}"
    else:
        text = bs.isoformat()
    return to_devnagari_numerals(text) if devnagari else text


def format_ad_date(ad: date, *, named: bool = False, devnagari: bool = False) -> str:
    """Format a Gregorian date as "2024-07-30", or "30 Jul 2024" when `named`.

    Parameters
    ----------
    ad : date
        The date to format.
    named : bool, optional
        Render as "day month year" instead of the ISO layout. Default is
        False.
    devnagari : bool, optional
        Render the digits in Devnagari. The month abbreviation stays Latin
        either way -- nepkit has no Devnagari names for the Gregorian
        calendar, the same rule the grid titles already follow. Default is
        False.

    Returns
    -------
    str
        The formatted date.
    """
    text = f"{ad.day} {AD_MONTH_ABBREVIATIONS[ad.month - 1]} {ad.year}" if named else ad.isoformat()
    return to_devnagari_numerals(text) if devnagari else text
