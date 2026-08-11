"""Command-line entry point for nepkit.

Deliberately thin. Everything about *what* to print lives in nepkit.render and
nepkit.convert; this module decides only where output goes and what exit code
to leave behind.

Exit codes:

    0  success
    2  usage error -- bad flag or unknown command (Typer's own)
    3  InvalidDateError     -- not a real date
    4  DateOutOfRangeError  -- a real date, but outside the bundled table

3 and 4 are separate on purpose. The exception hierarchy exists so a caller can
distinguish "you typed something that is not a date" from "that date is real
but I have no data for it"; collapsing both into 1 would throw that away at the
one boundary where it is most useful.
"""

import json
import shlex
import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from enum import StrEnum
from importlib.metadata import version
from typing import Annotated, Final

import typer
from rich.console import Console
from rich.panel import Panel
from typer.main import get_command

from nepkit.calendar_data import MAX_BS_YEAR, MIN_BS_YEAR
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import DateOutOfRangeError, InvalidDateError
from nepkit.render import (
    WEEKDAY_HEADER,
    MonthGrid,
    ad_month_grid,
    bs_month_grid,
    render_body_markup,
    render_plain,
)

EXIT_INVALID_DATE: Final[int] = 3
EXIT_OUT_OF_RANGE: Final[int] = 4

_DATE_PARTS: Final[int] = 3

app = typer.Typer(
    name="nepkit",
    help="Bikram Sambat <-> Gregorian date conversion.",
)

_PROMPT: Final[str] = "nepkit> "
_QUIT_WORDS: Final[frozenset[str]] = frozenset({"quit", "exit", "q"})


class ColorMode(StrEnum):
    """When to dress up calendar output. Grids only; conversions are never coloured."""

    auto = "auto"
    always = "always"
    never = "never"


def _today() -> date:
    """Seam for tests. Patch this rather than the clock itself."""
    return date.today()


def _stdin_is_interactive() -> bool:
    """Seam for tests, and the guard that keeps `nepkit` usable in a pipeline."""
    return sys.stdin.isatty()


def _dispatch(line: str) -> None:
    """Run one REPL line through the same command table the shell uses.

    standalone_mode=False makes Typer return the exit code instead of calling
    sys.exit, so a failing command ends the line rather than the session.
    """
    try:
        get_command(app).main(shlex.split(line), prog_name="nepkit", standalone_mode=False)
    except Exception as exc:
        # Deliberately broad. A typo must not throw the user out of the session,
        # and Typer's usage errors live in typer._click.exceptions -- a private
        # module this should not be importing to name them precisely.
        typer.echo(f"error: {exc}", err=True)


def _run_repl() -> None:
    typer.echo(f"nepkit {version('nepkit')} - Bikram Sambat <-> Gregorian")
    typer.echo("Type a command, 'help', or 'quit'.")
    while True:
        try:
            line = input(_PROMPT).strip()
        except EOFError:  # Ctrl-D
            typer.echo("")
            return
        except KeyboardInterrupt:  # Ctrl-C abandons the line, not the session
            typer.echo("")
            continue
        if not line:
            continue
        if line.lower() in _QUIT_WORDS:
            return
        _dispatch("--help" if line.lower() == "help" else line)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Bikram Sambat <-> Gregorian date conversion."""
    if ctx.invoked_subcommand is not None:
        return
    if not _stdin_is_interactive():
        # No terminal means no prompt: printing help and exiting 2 keeps the
        # old behaviour for scripts, which would otherwise block on stdin.
        typer.echo(ctx.get_help())
        raise typer.Exit(2)
    _run_repl()


@contextmanager
def _reported_as_exit_code() -> Generator[None, None, None]:
    """Turn nepkit's date errors into stderr messages and distinct exit codes."""
    try:
        yield
    except InvalidDateError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_INVALID_DATE) from exc
    except DateOutOfRangeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(EXIT_OUT_OF_RANGE) from exc


def _parse_ymd(text: str) -> tuple[int, int, int]:
    """Parse YYYY-MM-DD without regard to which calendar it belongs to.

    Both directions go through this so that identical garbage produces an
    identical exit code either way.
    """
    parts = text.split("-")
    if len(parts) != _DATE_PARTS or not all(part.isdigit() for part in parts):
        raise InvalidDateError(f"{text!r} is not a date in YYYY-MM-DD form")
    year, month, day = (int(part) for part in parts)
    return year, month, day


def _parse_bs(text: str) -> BSDate:
    year, month, day = _parse_ymd(text)
    return BSDate(year=year, month=month, day=day)  # validates against the table


def _parse_ad(text: str) -> date:
    year, month, day = _parse_ymd(text)
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise InvalidDateError(f"AD {text} is not a real Gregorian date") from exc


def _format_bs(bs: BSDate) -> str:
    return f"{bs.year:04d}-{bs.month:02d}-{bs.day:02d}"


def _emit_grid(grid: MonthGrid, kind: str, *, as_json: bool, color: ColorMode) -> None:
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "calendar": kind,
                    "title": grid.title,
                    "subtitle": grid.subtitle,
                    "today": grid.today,
                    "weeks": [list(week) for week in grid.weeks],
                }
            )
        )
        return

    coloured = color is ColorMode.always or (color is ColorMode.auto and Console().is_terminal)
    if not coloured:
        # render_plain, never render_body_markup: piped output stays inert, so a
        # grid does not change shape on the one day a month today falls in it.
        typer.echo(render_plain(grid))
        return

    # The subtitle goes inside the panel, not in its border: panel furniture is
    # clipped to the body width, and a span like "Ashadh 17 - Shrawan 16, 2081"
    # is wider than the 27-column grid, so the border ate the year.
    body = f"[dim]{grid.subtitle.center(len(WEEKDAY_HEADER))}[/dim]\n{render_body_markup(grid)}"
    Console(force_terminal=True).print(
        Panel.fit(body, title=f"[bold]{grid.title}[/bold]", border_style="cyan")
    )


JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
ColorOption = Annotated[ColorMode, typer.Option("--color", help="When to colourise the grid.")]
YearArg = Annotated[int | None, typer.Argument(help="Year. Defaults to the current one.")]
MonthArg = Annotated[int | None, typer.Argument(help="Month, 1-12. Defaults to the current one.")]


@app.command("bs2ad")
def bs_to_ad_command(
    bs_date: Annotated[str, typer.Argument(metavar="BS_DATE", help="Bikram Sambat YYYY-MM-DD.")],
    as_json: JsonOption = False,
) -> None:
    """Convert a Bikram Sambat date to Gregorian."""
    with _reported_as_exit_code():
        bs = _parse_bs(bs_date)
        ad = bs_to_ad(bs)
    if as_json:
        typer.echo(json.dumps({"bs": _format_bs(bs), "ad": ad.isoformat()}))
    else:
        typer.echo(ad.isoformat())


@app.command("ad2bs")
def ad_to_bs_command(
    ad_date: Annotated[str, typer.Argument(metavar="AD_DATE", help="Gregorian YYYY-MM-DD.")],
    as_json: JsonOption = False,
) -> None:
    """Convert a Gregorian date to Bikram Sambat."""
    with _reported_as_exit_code():
        ad = _parse_ad(ad_date)
        bs = ad_to_bs(ad)
    if as_json:
        typer.echo(json.dumps({"bs": _format_bs(bs), "ad": ad.isoformat()}))
    else:
        typer.echo(_format_bs(bs))


@app.command("today")
def today_command(as_json: JsonOption = False) -> None:
    """Print today's date in both calendars."""
    ad = _today()
    with _reported_as_exit_code():
        bs = ad_to_bs(ad)
    if as_json:
        typer.echo(json.dumps({"bs": _format_bs(bs), "ad": ad.isoformat()}))
        return
    # Two labelled lines, the same shape `range` prints, so the two commands
    # that report a position in both calendars read alike.
    typer.echo(f"BS {_format_bs(bs)}")
    typer.echo(f"AD {ad.isoformat()}")


@app.command("range")
def range_command(as_json: JsonOption = False) -> None:
    """Print the date range nepkit has data for."""
    bs_min, bs_max = f"{MIN_BS_YEAR:04d}-01-01", _format_bs(ad_to_bs(MAX_AD_DATE))
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "bs": {"min": bs_min, "max": bs_max},
                    "ad": {"min": MIN_AD_DATE.isoformat(), "max": MAX_AD_DATE.isoformat()},
                }
            )
        )
        return
    typer.echo(f"BS {bs_min} .. {bs_max}  (years {MIN_BS_YEAR}-{MAX_BS_YEAR})")
    typer.echo(f"AD {MIN_AD_DATE.isoformat()} .. {MAX_AD_DATE.isoformat()}")


@app.command("calbs")
def calbs_command(
    year: YearArg = None,
    month: MonthArg = None,
    as_json: JsonOption = False,
    color: ColorOption = ColorMode.auto,
) -> None:
    """Display a Bikram Sambat month."""
    with _reported_as_exit_code():
        current = ad_to_bs(_today()) if MIN_AD_DATE <= _today() <= MAX_AD_DATE else None
        if year is None or month is None:
            if current is None:
                raise DateOutOfRangeError(
                    f"today ({_today().isoformat()}) is outside the convertible window, "
                    "so there is no current BS month to default to"
                )
            year, month = year or current.year, month or current.month
        grid = bs_month_grid(year, month, today=current)
    _emit_grid(grid, "bs", as_json=as_json, color=color)


@app.command("calad")
def calad_command(
    year: YearArg = None,
    month: MonthArg = None,
    as_json: JsonOption = False,
    color: ColorOption = ColorMode.auto,
) -> None:
    """Display a Gregorian month."""
    with _reported_as_exit_code():
        today = _today()
        grid = ad_month_grid(year or today.year, month or today.month, today=today)
    _emit_grid(grid, "ad", as_json=as_json, color=color)
