# Contributing

nepkit is a small, typed library with one collaborator today, but the process
below is the same one used for every change, including mine — that's what
makes CI meaningful rather than decorative.

## Setup

```bash
git clone https://github.com/akakritagya/nepkit
cd nepkit
uv sync --group dev
uv run pre-commit install                         # lint/format/type-check on commit
uv run pre-commit install --hook-type commit-msg  # enforce Conventional Commits
uv run pre-commit install --hook-type pre-push    # full test suite before push
```

See the [README's Development section](README.md#development) for what each
hook checks and why the test suite runs at push time rather than every commit.

## Before opening a PR

```bash
uv run pytest                # tests
uv run ruff check .          # lint
uv run ruff format --check . # format
uv run mypy                  # types
```

These are exactly the checks CI runs, so a clean local run means a green PR,
not a surprise later. `pre-commit` catches most of this automatically if
installed.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/), enforced by the
`commit-msg` hook: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`,
optionally scoped (`feat(cli): ...`). The changelog and release notes are
generated from these, so an inaccurate prefix is not cosmetic.

## Data changes

If a change touches `src/nepkit/data/`, read
[`DATA.md`](src/nepkit/data/DATA.md) first. The calendar table is the part of
this project that tests cannot verify by construction — see the README's
[Limitations](README.md#limitations) section for why round-trip tests pass
even when the table is wrong. A data change needs a second independent source
cross-checked row by row, not just green tests.

## Pull requests

`main` requires a passing PR — direct pushes don't merge. CI runs lint,
format, type-check, the test matrix (Python 3.12–3.14), and a Windows/Git Bash
job that exercises the install and completion paths described in the README.
All of it has to pass; there's no path that skips a check because the change
looks small.

Branch from `main`, keep the change focused, and let the description explain
*why* if the diff alone doesn't make it obvious — same standard as the code
itself.

## Reporting bugs and requesting features

Use the issue templates — they ask for the version, platform, and a
reproduction, which is most of what's needed to act on a report.

Security issues are the one exception: see [SECURITY.md](SECURITY.md) instead
of opening a public issue.
