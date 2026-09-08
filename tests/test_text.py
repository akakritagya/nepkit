"""Date <-> human text: parsing, formatting, month names, weekday names, Devnagari digits."""

import calendar
from datetime import date

import pytest

from nepkit.calendar_data import BS_MONTH_ALIASES, BS_MONTH_NAMES, BS_MONTH_NAMES_NE
from nepkit.convert import BSDate
from nepkit.exceptions import CalendarDataError, DateOutOfRangeError, InvalidDateError
from nepkit.text import (
    _AD_MONTH_LOOKUP,
    _BS_MONTH_LOOKUP,
    AD_MONTH_ABBREVIATIONS,
    AD_MONTH_NAMES,
    WEEKDAY_ABBREVIATIONS,
    WEEKDAY_ABBREVIATIONS_NE,
    _build_bs_month_lookup,
    bs_month_name,
    format_ad_date,
    format_bs_date,
    parse_ad_date,
    parse_ad_month,
    parse_bs_date,
    parse_bs_month,
    to_devnagari_numerals,
    weekday_name,
)


def test_bs_month_name_looks_up_by_1_based_month_number() -> None:
    assert bs_month_name(4) == "Shrawan"


def test_bs_month_name_devnagari_looks_up_the_devnagari_table() -> None:
    assert bs_month_name(4, devnagari=True) == "साउन"


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2024, 7, 28), "Sun"),
        (date(2024, 7, 29), "Mon"),
        (date(2024, 7, 30), "Tue"),
        (date(2024, 7, 31), "Wed"),
        (date(2024, 8, 1), "Thu"),
        (date(2024, 8, 2), "Fri"),
        (date(2024, 8, 3), "Sat"),
    ],
)
def test_weekday_name_covers_a_whole_week(day: date, expected: str) -> None:
    """One known week, so an off-by-one in the Sunday-first shift cannot hide."""
    assert weekday_name(day) == expected


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2024, 7, 28), "आइत"),
        (date(2024, 7, 29), "सोम"),
        (date(2024, 7, 30), "मंगल"),
        (date(2024, 7, 31), "बुध"),
        (date(2024, 8, 1), "बिही"),
        (date(2024, 8, 2), "शुक्र"),
        (date(2024, 8, 3), "शनि"),
    ],
)
def test_weekday_name_devnagari_covers_a_whole_week(day: date, expected: str) -> None:
    assert weekday_name(day, devnagari=True) == expected


def test_weekday_abbreviations_ne_drop_the_baar_suffix() -> None:
    assert WEEKDAY_ABBREVIATIONS_NE == ("आइत", "सोम", "मंगल", "बुध", "बिही", "शुक्र", "शनि")
    assert len(WEEKDAY_ABBREVIATIONS_NE) == len(WEEKDAY_ABBREVIATIONS)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0123456789", "०१२३४५६७८९"),
        ("2081-04-15", "२०८१-०४-१५"),
        ("no digits here", "no digits here"),
        ("", ""),
        ("Jul 16, 2024", "Jul १६, २०२४"),
    ],
)
def test_to_devnagari_numerals_translates_only_ascii_digits(text: str, expected: str) -> None:
    assert to_devnagari_numerals(text) == expected


def test_to_devnagari_numerals_is_idempotent_on_already_devnagari_text() -> None:
    once = to_devnagari_numerals("2081")
    assert to_devnagari_numerals(once) == once


def test_ad_month_names_and_abbreviations_line_up() -> None:
    assert len(AD_MONTH_NAMES) == 12
    assert AD_MONTH_NAMES[6] == "July"
    assert tuple(name[:3] for name in AD_MONTH_NAMES) == AD_MONTH_ABBREVIATIONS


def test_ad_month_names_are_unaffected_by_the_locale_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sabotage the locale-sensitive stdlib objects the old implementation read.
    # If nepkit consults them at all -- at import or at call time -- this fails.
    monkeypatch.setattr(calendar, "month_name", ["", *(["XXXXXXX"] * 12)])
    monkeypatch.setattr(calendar, "month_abbr", ["", *(["XXX"] * 12)])
    assert AD_MONTH_NAMES[6] == "July"
    assert AD_MONTH_ABBREVIATIONS[6] == "Jul"


# --- Month lookups -----------------------------------------------------------


def test_bs_and_ad_month_lookups_share_no_key() -> None:
    # A single input string that resolved in both calendars could silently
    # convert as the wrong one -- e.g. a future alias shortened to "mar"
    # would collide with March. Disjointness is what rules that out.
    assert _BS_MONTH_LOOKUP.keys().isdisjoint(_AD_MONTH_LOOKUP.keys())


def test_bs_month_lookup_covers_every_canonical_alias_and_devnagari_name() -> None:
    expected = len(BS_MONTH_NAMES) + len(BS_MONTH_NAMES_NE)
    expected += sum(len(aliases) for aliases in BS_MONTH_ALIASES)
    assert len(_BS_MONTH_LOOKUP) == expected


def test_build_bs_month_lookup_rejects_an_alias_claimed_by_two_months(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # BS_MONTH_ALIASES itself is collision-free (test_calendar_data.py pins
    # that); this proves the builder would actually catch it if it were not.
    colliding = (("baisakh",), ("baisakh",), *(() for _ in range(10)))
    monkeypatch.setattr("nepkit.text.BS_MONTH_ALIASES", colliding)
    with pytest.raises(CalendarDataError, match="maps to both month 1 and 2"):
        _build_bs_month_lookup()


@pytest.mark.parametrize(
    ("text", "expected"),
    [("4", 4), ("Shrawan", 4), ("shrawan", 4), ("SHRAWAN", 4), ("Baishakh", 1), ("साउन", 4)],
    ids=["numeric", "canonical", "lowercase", "uppercase", "alias", "devnagari"],
)
def test_parse_bs_month_accepts_numbers_names_aliases_and_devnagari(
    text: str, expected: int
) -> None:
    assert parse_bs_month(text) == expected


def test_parse_bs_month_rejects_an_unrecognised_word() -> None:
    with pytest.raises(InvalidDateError, match="not a recognised month name"):
        parse_bs_month("Notamonth")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("7", 7), ("July", 7), ("july", 7), ("Jul", 7), ("JUL", 7)],
    ids=["numeric", "full_name", "lowercase", "abbreviation", "uppercase_abbreviation"],
)
def test_parse_ad_month_accepts_numbers_names_and_abbreviations(text: str, expected: int) -> None:
    assert parse_ad_month(text) == expected


def test_parse_ad_month_rejects_an_unrecognised_word() -> None:
    with pytest.raises(InvalidDateError, match="not a recognised month name"):
        parse_ad_month("Notamonth")


# --- parse_bs_date / parse_ad_date -------------------------------------------


def test_parse_bs_date_accepts_numeric_form() -> None:
    assert parse_bs_date("2081-04-15") == BSDate(2081, 4, 15)


def test_parse_bs_date_accepts_the_canonical_named_form() -> None:
    assert parse_bs_date("15 Shrawan 2081") == BSDate(2081, 4, 15)


def test_parse_bs_date_accepts_a_romanisation_variant() -> None:
    assert parse_bs_date("15 Sawan 2081") == BSDate(2081, 4, 15)


def test_parse_bs_date_accepts_a_fully_devnagari_date() -> None:
    assert parse_bs_date("१५ साउन २०८१") == BSDate(2081, 4, 15)


def test_parse_bs_date_rejects_an_unrecognised_month_word() -> None:
    with pytest.raises(InvalidDateError, match="not a recognised month name"):
        parse_bs_date("15 Notamonth 2081")


def test_parse_bs_date_rejects_text_in_neither_form() -> None:
    with pytest.raises(InvalidDateError, match="not a date in"):
        parse_bs_date("not a date")


def test_parse_bs_date_still_validates_against_the_table() -> None:
    with pytest.raises(DateOutOfRangeError):
        parse_bs_date("2095-01-01")


def test_parse_ad_date_accepts_numeric_form() -> None:
    assert parse_ad_date("2024-07-30") == date(2024, 7, 30)


def test_parse_ad_date_accepts_full_month_name() -> None:
    assert parse_ad_date("30 July 2024") == date(2024, 7, 30)


def test_parse_ad_date_accepts_month_abbreviation() -> None:
    assert parse_ad_date("30 Jul 2024") == date(2024, 7, 30)


def test_parse_ad_date_rejects_an_unrecognised_month_word() -> None:
    with pytest.raises(InvalidDateError, match="not a recognised month name"):
        parse_ad_date("30 Notamonth 2024")


def test_parse_ad_date_rejects_text_in_neither_form() -> None:
    with pytest.raises(InvalidDateError, match="not a date in"):
        parse_ad_date("not a date")


def test_parse_ad_date_rejects_a_numeric_date_that_does_not_exist() -> None:
    with pytest.raises(InvalidDateError, match="not a real Gregorian date"):
        parse_ad_date("2024-02-30")


# --- format_bs_date / format_ad_date -----------------------------------------


def test_format_bs_date_default_is_exactly_isoformat() -> None:
    bs = BSDate(2081, 4, 15)
    assert format_bs_date(bs) == bs.isoformat()


def test_format_bs_date_named() -> None:
    assert format_bs_date(BSDate(2081, 4, 15), named=True) == "15 Shrawan 2081"


def test_format_bs_date_named_devnagari() -> None:
    assert format_bs_date(BSDate(2081, 4, 15), named=True, devnagari=True) == "१५ साउन २०८१"


def test_format_bs_date_devnagari_without_named_translates_digits_only() -> None:
    assert format_bs_date(BSDate(2081, 4, 15), devnagari=True) == "२०८१-०४-१५"


def test_format_ad_date_default_is_exactly_isoformat() -> None:
    ad = date(2024, 7, 30)
    assert format_ad_date(ad) == ad.isoformat()


def test_format_ad_date_named() -> None:
    assert format_ad_date(date(2024, 7, 30), named=True) == "30 Jul 2024"


def test_format_ad_date_named_devnagari_translates_digits_but_keeps_the_month_name_latin() -> None:
    assert format_ad_date(date(2024, 7, 30), named=True, devnagari=True) == "३० Jul २०२४"


@pytest.mark.parametrize("devnagari", [False, True], ids=["latin", "devnagari"])
def test_every_named_bs_format_parses_back_to_the_same_date(devnagari: bool) -> None:
    bs = BSDate(2081, 4, 15)
    formatted = format_bs_date(bs, named=True, devnagari=devnagari)
    assert parse_bs_date(formatted) == bs
