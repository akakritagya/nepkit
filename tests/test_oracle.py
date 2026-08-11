"""Tier 3: the only tests here that can detect a wrong calendar.json.

Tiers 1 and 2 are self-referential. The loader tests prove malformed data is
rejected; the property tests prove the two conversion directions are mutual
inverses across all 33,238 days. Neither can see a month length that is
well-formed and simply wrong, because both directions read the same table and
the error cancels exactly. That was verified by deliberately corrupting the
table: every property still passed while conversions were silently wrong.

These tests close that gap by asserting against dates established outside this
codebase entirely -- historical events recorded in both calendars by sources
with no connection to nepkit, to calendar.json, or to either of the two GitHub
tables in data/DATA.md.

Two honest limits:

* This tier is a sample, not a proof. Tier 2 is exhaustive; full external
  verification would need 33,238 attested pairs, which do not exist. An anchor
  error shifts every conversion uniformly, so any one pair catches it. A month
  table error shifts only a window and heals afterwards, so a corruption
  sitting between two pairs can still hide. Pairs are spread across decades
  for that reason, not for volume.
* Nothing here is machine-checkable against its source. The dataclass forces a
  citation to exist and records what the source actually asserts, so a reviewer
  can check it in one click. It cannot stop someone writing down a date they
  half-remember -- which is the failure mode that would quietly undo the whole
  data-sourcing exercise, so it is worth naming rather than assuming away.

BS months: 1 Baisakh, 2 Jestha, 3 Ashadh, 4 Shrawan, 5 Bhadra, 6 Ashoj,
7 Kartik, 8 Mangsir, 9 Poush, 10 Magh, 11 Falgun, 12 Chaitra.
"""

from dataclasses import dataclass
from datetime import date

import pytest

from nepkit import BSDate, ad_to_bs, bs_to_ad


@dataclass(frozen=True, slots=True)
class OraclePair:
    """A BS<->AD correspondence attested outside this codebase.

    `sources` and `states` have no defaults on purpose: an uncited pair is a
    TypeError at import rather than something a reviewer has to notice. Same
    move as BSDate validating in __post_init__ -- push the rule into the type
    instead of relying on anyone remembering it.
    """

    event: str
    bs: BSDate
    ad: date
    sources: tuple[str, ...]
    states: str


ORACLE_PAIRS: tuple[OraclePair, ...] = (
    OraclePair(
        event="rana rule ends",
        bs=BSDate(2007, 11, 7),
        ad=date(1951, 2, 18),
        sources=("https://www.imnepal.com/falgun-7-democracy-day-nepal-prajatantra-diwas/",),
        states="Democracy Day is Falgun 7, marking democracy established in 1951 AD (2007 BS).",
    ),
    OraclePair(
        event="jana andolan i begins",
        bs=BSDate(2046, 11, 7),
        ad=date(1990, 2, 18),
        sources=("https://en.wikipedia.org/wiki/1990_Nepalese_revolution",),
        states="The movement 'officially started on 18 February 1990 (BS २०४६ फागुन ०७)'.",
    ),
    OraclePair(
        event="narayanhiti royal massacre",
        bs=BSDate(2058, 2, 19),
        ad=date(2001, 6, 1),
        sources=("https://en.wikipedia.org/wiki/Nepalese_royal_massacre",),
        states="Infobox gives '1 June 2001' and '19 Jestha 2058 Nepal B.S.' together.",
    ),
    OraclePair(
        event="federal republic declared",
        bs=BSDate(2065, 2, 15),
        ad=date(2008, 5, 28),
        sources=(
            "https://nepalipatro.com.np/blog/en/republic-day/",
            "https://en.wikipedia.org/wiki/Republic_Day_(Nepal)",
        ),
        states=(
            "Nepali Patro dates the first Constituent Assembly meeting that abolished the "
            "monarchy to 'B.S. 2065, Jestha 15th'; Wikipedia dates the same meeting to "
            "28 May 2008. Neither converted anything -- each recorded it natively."
        ),
    ),
    OraclePair(
        event="constitution promulgated",
        bs=BSDate(2072, 6, 3),
        ad=date(2015, 9, 20),
        sources=("https://nepalipatro.com.np/blog/en/constitution-day/",),
        states="Constitution Day is Asoj 3, commemorating promulgation on Asoj 3, 2072 BS "
        "(September 20, 2015).",
    ),
    OraclePair(
        event="nepali new year 2081",
        bs=BSDate(2081, 1, 1),
        ad=date(2024, 4, 13),
        sources=("https://anmn.org/saturday-13th-april-2024-proclaimed-as-nepali-new-year/",),
        states="Saturday 13 April 2024 proclaimed as Nepali New Year 2081, i.e. Baisakh 1.",
    ),
)

_IDS = [pair.event.replace(" ", "_") for pair in ORACLE_PAIRS]


@pytest.mark.parametrize("pair", ORACLE_PAIRS, ids=_IDS)
def test_bs_to_ad_matches_an_externally_attested_date(pair: OraclePair) -> None:
    assert bs_to_ad(pair.bs) == pair.ad, (
        f"{pair.event}: sources say AD {pair.ad.isoformat()}, nepkit says "
        f"{bs_to_ad(pair.bs).isoformat()} -- see {pair.sources[0]}"
    )


@pytest.mark.parametrize("pair", ORACLE_PAIRS, ids=_IDS)
def test_ad_to_bs_matches_an_externally_attested_date(pair: OraclePair) -> None:
    assert ad_to_bs(pair.ad) == pair.bs, (
        f"{pair.event}: sources say BS {pair.bs.year}-{pair.bs.month:02d}-{pair.bs.day:02d}, "
        f"nepkit says {ad_to_bs(pair.ad)} -- see {pair.sources[0]}"
    )


def test_the_anchor_is_confirmed_by_the_earliest_external_pair() -> None:
    """ANCHOR.ad_date has no other check anywhere in the suite.

    It is the one Gregorian fact that cannot be derived from calendar.json, so
    nothing inside the package can verify it. An anchor error shifts all 33,238
    conversions by the same amount, which means any single correct external
    pair detects it -- this names the one nearest the anchor so a failure here
    points at the anchor rather than at some distant month.
    """
    earliest = min(ORACLE_PAIRS, key=lambda pair: pair.ad)
    assert bs_to_ad(earliest.bs) == earliest.ad


def test_every_pair_carries_a_resolvable_citation() -> None:
    """The required field stops a missing source; this stops a placeholder one."""
    for pair in ORACLE_PAIRS:
        assert pair.sources, f"{pair.event} has no source"
        assert all(url.startswith("https://") for url in pair.sources), pair.event
        assert pair.states.strip(), f"{pair.event} does not record what its source says"


def test_pairs_are_spread_across_the_range_rather_than_clustered() -> None:
    """Clustered pairs all probe the same interval.

    A month-table error affects only dates between the bad month and the next
    compensating one, so six pairs from one decade would be barely better than
    one. This encodes the spread as a check so it survives future additions.
    """
    decades = {pair.ad.year // 10 for pair in ORACLE_PAIRS}
    assert len(decades) >= 5, f"pairs only cover decades {sorted(decades)}"
