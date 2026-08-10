# nepkit

Nepal-specific developer utilities. Bikram Sambat ↔ Gregorian date conversion,
with currency and unit helpers planned.

> **Status:** early scaffolding — package layout and tooling are in place;
> conversion logic is not implemented yet.

## Why

Bikram Sambat conversion in Python is scattered across a handful of small,
mostly unmaintained packages, each with its own API, a hardcoded and often
undocumented year range, and no type hints. None of them pair the date logic
with the other Nepal-specific conversions (currency formatting, units) that
tend to show up in the same projects, so you end up pulling in several
half-maintained dependencies instead of one. nepkit aims to be a single,
typed, well-tested toolkit for these instead.

## Install

Requires Python 3.12+. This project uses [uv](https://docs.astral.sh/uv/) for
dependency and environment management.

```bash
uv sync
```

## Usage

```bash
uv run nepkit
```

The `nepkit` CLI (built with [Typer](https://typer.tiangolo.com/)) is wired up
but doesn't expose any commands yet — `nepkit date` conversion is the first
one planned.

## Development

```bash
uv sync --group dev          # install dev dependencies (pytest, ruff, mypy, pre-commit)
uv run pytest                # run tests
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # type check
uv run pre-commit install                     # one-time: lint/format/type-check on every commit
uv run pre-commit install --hook-type commit-msg  # one-time: enforce Conventional Commits
uv run pre-commit install --hook-type pre-push    # one-time: run the full test suite before push
```

`pre-commit` runs lint, format, and type-check on every commit; blocks large
files, private keys, and direct commits to `main`; runs the full `pytest`
suite before `push` (not on every commit — too slow to survive contact with
a growing suite); and enforces [Conventional
Commits](https://www.conventionalcommits.org/) on the commit message.
