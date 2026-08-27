#!/usr/bin/env python3
"""Re-verify calendar.json's bundled range against its two upstream sources.

DATA.md documents a one-time manual diff between source A and source B, done
with a throwaway script never checked into this repo. This is that check made
rerunnable: fetch both sources' current tables, diff them against each other
and against nepkit's own shipped calendar.json over the bundled BS range, and
exit non-zero on any disagreement -- so a later revision to either upstream
table surfaces here instead of silently outliving the one-time check that
originally justified trusting the data.

    uv run python scripts/verify_calendar_sources.py
"""

import json
import re
import sys
from urllib.request import urlopen

from nepkit.calendar_data import MAX_BS_YEAR, MIN_BS_YEAR, days_in_month

SOURCE_A_URL = (
    "https://raw.githubusercontent.com/medic/bikram-sambat/master/test-data/daysInMonth.json"
)
SOURCE_B_URL = "https://raw.githubusercontent.com/sbmdkl/nepali-date-converter/main/src/config.ts"

_SOURCE_B_ROW = re.compile(r"BS\[(\d+)\]\s*=\s*\[([\d,\s]+)\];")


def _fetch(url: str) -> str:
    """Fetch `url`'s body as text.

    Parameters
    ----------
    url : str
        An https URL -- always one of the two module-level constants above,
        never external input.

    Returns
    -------
    str
        The response body, decoded as UTF-8.
    """
    with urlopen(url, timeout=30) as response:
        body: bytes = response.read()
        return body.decode("utf-8")


def parse_source_a(raw: str) -> dict[int, tuple[int, ...]]:
    """Parse source A's `{"year": [12 ints]}` JSON into year -> month lengths.

    Raises
    ------
    ValueError
        If `raw` is not shaped the way source A's format is documented to be.
    """
    data: object = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("source A: expected a JSON object of {year: [12 ints]}")
    result: dict[int, tuple[int, ...]] = {}
    for year, months in data.items():
        if not isinstance(months, list) or not all(isinstance(m, int) for m in months):
            raise ValueError(f"source A: BS {year} row is not a list of ints")
        result[int(year)] = tuple(months)
    return result


def parse_source_b(raw: str) -> dict[int, tuple[int, ...]]:
    """Parse source B's `BS[year] = [year, ...12 ints];` rows into year -> month lengths."""
    result: dict[int, tuple[int, ...]] = {}
    for match in _SOURCE_B_ROW.finditer(raw):
        year = int(match.group(1))
        numbers = [int(n) for n in match.group(2).split(",")]
        result[year] = tuple(numbers[1:])  # numbers[0] echoes the year, not a month length
    return result


def load_shipped_calendar() -> dict[int, tuple[int, ...]]:
    """Read nepkit's own bundled table through its validated loader."""
    return {
        year: tuple(days_in_month(year, month) for month in range(1, 13))
        for year in range(MIN_BS_YEAR, MAX_BS_YEAR + 1)
    }


def find_mismatches(
    source_a: dict[int, tuple[int, ...]],
    source_b: dict[int, tuple[int, ...]],
    shipped: dict[int, tuple[int, ...]],
) -> list[str]:
    """Diff all three tables over the bundled BS range and describe every disagreement."""
    problems: list[str] = []
    for year in range(MIN_BS_YEAR, MAX_BS_YEAR + 1):
        a, b, s = source_a.get(year), source_b.get(year), shipped[year]
        if a is None:
            problems.append(f"BS {year}: missing from source A")
        elif b is None:
            problems.append(f"BS {year}: missing from source B")
        elif a != b:
            problems.append(f"BS {year}: source A {a} disagrees with source B {b}")
        elif a != s:
            problems.append(f"BS {year}: sources agree on {a} but calendar.json has {s}")
    return problems


def main() -> int:
    """Fetch both sources, diff them against each other and calendar.json, report, and exit."""
    source_a = parse_source_a(_fetch(SOURCE_A_URL))
    source_b = parse_source_b(_fetch(SOURCE_B_URL))
    shipped = load_shipped_calendar()

    problems = find_mismatches(source_a, source_b, shipped)
    if problems:
        print(f"{len(problems)} mismatch(es) over BS {MIN_BS_YEAR}-{MAX_BS_YEAR}:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(f"OK: source A, source B, and calendar.json agree over BS {MIN_BS_YEAR}-{MAX_BS_YEAR}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
