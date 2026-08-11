"""Tier 2: properties that must hold across the whole bundled domain.

These assert relations rather than answers, so they need no oracle -- which is
exactly why they cannot detect a wrong calendar.json. Both conversion
directions read the same table, so a bad month length cancels out and every
property here still passes. See data/DATA.md for the sourcing that guards
against that, and the tier-3 tests for the external checks that can see it.

The domain is 33,238 days, small enough to enumerate exhaustively in well under
a second, so there is nothing here for a random-generation library to improve
on: these cover every input, not a sample of them.
"""

from datetime import timedelta

from nepkit.calendar_data import TOTAL_DAYS, bs_from_days, days_from_anchor
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, ad_to_bs, bs_to_ad


def test_every_day_count_round_trips_through_bs_from_days() -> None:
    """bs_from_days and days_from_anchor are mutual inverses over the whole span.

    The two reach their answers by different routes -- bisect plus a month walk
    versus a cumulative offset plus a sum -- so agreement across every day is
    real evidence, not one function checking its own arithmetic.
    """
    for days in range(TOTAL_DAYS):
        year, month, day = bs_from_days(days)
        collapsed = days_from_anchor(year, month, day)
        assert collapsed == days, (
            f"day {days} expanded to BS {year}-{month:02d}-{day:02d}, "
            f"which collapses back to {collapsed}"
        )


def test_consecutive_day_counts_are_consecutive_bs_dates() -> None:
    """Adding one day advances the BS date by exactly one day, with no gaps or repeats.

    Deliberately never calls days_from_anchor: it checks the shape of the output
    sequence on its own terms. If the two conversion directions ever acquire
    bugs that cancel, the round-trip property keeps passing and this is what
    fails.
    """
    previous = bs_from_days(0)
    for days in range(1, TOTAL_DAYS):
        year, month, day = bs_from_days(days)
        prev_year, prev_month, prev_day = previous
        same_month = (year, month) == (prev_year, prev_month) and day == prev_day + 1
        next_month = year == prev_year and month == prev_month + 1 and day == 1
        next_year = year == prev_year + 1 and (month, day) == (1, 1)
        assert same_month or next_month or next_year, (
            f"day {days}: BS {prev_year}-{prev_month:02d}-{prev_day:02d} is followed by "
            f"BS {year}-{month:02d}-{day:02d}, which is not the next day"
        )
        previous = (year, month, day)


def test_every_ad_date_in_the_window_round_trips() -> None:
    """Every convertible AD date survives a trip through BS and back.

    The only property that exercises the AD window bounds and the direction of
    the timedelta arithmetic; the day-count properties never touch either.
    """
    ad = MIN_AD_DATE
    while ad <= MAX_AD_DATE:
        assert bs_to_ad(ad_to_bs(ad)) == ad, f"AD {ad.isoformat()} did not survive a round trip"
        ad += timedelta(days=1)
