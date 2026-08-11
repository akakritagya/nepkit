# Provenance — `calendar.json`

`calendar.json` holds Bikram Sambat (BS) month-length data for BS 2000–2090
(≈ AD 1943–2034). This file records where those numbers came from and how
they were verified, per the sourcing process below. Last verified: 2026-08-06.

## Sources

**A — [medic/bikram-sambat](https://github.com/medic/bikram-sambat)**
JS/Java library, Apache-2.0, maintained by Medic Mobile for health-data
tooling deployed in Nepal. Table fetched from `test-data/daysInMonth.json`
at commit `1aabdf9d6dd9ab560f289fc0427ae410cfd523c2`. Covers BS 1970–2090.
Its own conversion epoch, hardcoded in `js/src/index.js`, is
`BS 1970-01-01 = AD 1913-04-13`.

**B — [sbmdkl/nepali-date-converter](https://github.com/sbmdkl/nepali-date-converter)**
npm package, unrelated author and codebase to source A. Table fetched from
`src/config.ts` at commit `143121857b31822ddbc8bf50cdd918b79e267a96`. Covers
BS 1978–2099. Its own epoch, from `src/config.ts`, is
`BS 1978-01-01 = AD 1921-04-13`. No license is declared on this repo — the
day-count values are treated as facts (not creative expression) used solely
to cross-check source A, not as copied code or copied text.

## Verification method

1. Fetched both tables' raw source files directly (not via any
   already-published "combined" dataset).
2. Validated each source independently over BS 2000–2090: 12 months per
   year, every month's day-count in the plausible range 29–32.
3. Diffed the two tables row by row over BS 2000–2090 (91 years, 1092
   month-values). **Result: empty diff** — full agreement, no disagreements
   needed a third-source tiebreak.
4. Cross-checked every reconciled year's total against 365/366 days — all
   pass.
5. Anchor check: walked each source forward from its own epoch, through its
   own month table, to BS 2000-01-01. Source A and source B — starting from
   different epochs, 8 years apart — land on the same date:
   **BS 2000-01-01 = AD 1943-04-14**. A third, independently-computed public
   date-converter tool (unrelated codebase to A or B) states the same
   pairing. This is the value pinned as `ANCHOR` in `calendar_data.py`.

Script used for steps 2–4 was a throwaway (`diff_sources.py`, not checked
into this repo) — the empty diff and the reconciled table it produced are
what's committed here, not the script itself.

## Scope

Only BS 2000–2090 is shipped, even though both sources cover more (A goes
back to 1970, B goes up to 2099) — this matches the range decided for
nepkit. If the range ever needs to extend past 2090 or before 2000, redo
this sourcing process for the new years rather than assuming either source
is reliable outside the range checked here.
