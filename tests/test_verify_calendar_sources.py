"""scripts/verify_calendar_sources.py's pure logic: parsing and diffing, no network.

`main` and `_fetch` are the only pieces that touch the network, deliberately left
untested here -- a unit test suite that hits GitHub on every run would make CI
flaky on nepkit's own account, not on the sources'. They're exercised by actually
running the script (manually, or in the scheduled CI job), same as any other
integration-shaped edge.
"""

import pytest
from verify_calendar_sources import (
    find_mismatches,
    load_shipped_calendar,
    parse_source_a,
    parse_source_b,
)

from nepkit.calendar_data import MAX_BS_YEAR, MIN_BS_YEAR


def test_parse_source_a_reads_year_to_months() -> None:
    raw = '{"2000": [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30]}'
    assert parse_source_a(raw) == {2000: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30)}


def test_parse_source_a_rejects_a_non_object() -> None:
    with pytest.raises(ValueError, match="expected a JSON object"):
        parse_source_a("[1, 2, 3]")


def test_parse_source_b_reads_year_to_months_dropping_the_leading_year() -> None:
    raw = "BS[2000] = [2000, 31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30];"
    assert parse_source_b(raw) == {2000: (31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30)}


def test_parse_source_b_reads_every_row_in_a_multi_line_file() -> None:
    raw = (
        "BS[2000] = [2000, 31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30];\n"
        "BS[2001] = [2001, 30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31];\n"
    )
    result = parse_source_b(raw)
    assert set(result) == {2000, 2001}


def test_load_shipped_calendar_matches_the_bundled_range() -> None:
    shipped = load_shipped_calendar()
    assert set(shipped) == set(range(MIN_BS_YEAR, MAX_BS_YEAR + 1))
    assert all(len(months) == 12 for months in shipped.values())


def test_find_mismatches_is_empty_when_all_three_agree() -> None:
    shipped = load_shipped_calendar()
    assert find_mismatches(shipped, shipped, shipped) == []


def test_find_mismatches_reports_a_disagreement_between_source_a_and_source_b() -> None:
    shipped = load_shipped_calendar()
    corrupted = dict(shipped)
    a_year = MIN_BS_YEAR
    corrupted[a_year] = (99, *corrupted[a_year][1:])

    problems = find_mismatches(corrupted, shipped, shipped)

    assert len(problems) == 1
    assert f"BS {a_year}" in problems[0]
    assert "disagrees" in problems[0]


def test_find_mismatches_reports_sources_agreeing_against_a_wrong_shipped_value() -> None:
    shipped = load_shipped_calendar()
    corrupted_shipped = dict(shipped)
    a_year = MAX_BS_YEAR
    corrupted_shipped[a_year] = (99, *corrupted_shipped[a_year][1:])

    problems = find_mismatches(shipped, shipped, corrupted_shipped)

    assert len(problems) == 1
    assert f"BS {a_year}" in problems[0]
    assert "calendar.json has" in problems[0]


def test_find_mismatches_reports_a_year_missing_from_source_a() -> None:
    shipped = load_shipped_calendar()
    incomplete = dict(shipped)
    del incomplete[MIN_BS_YEAR]

    problems = find_mismatches(incomplete, shipped, shipped)

    assert len(problems) == 1
    assert f"BS {MIN_BS_YEAR}: missing from source A" in problems[0]
