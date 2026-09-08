"""Command-line entry point for nepkit.

Deliberately thin. Everything about *what* to print lives in nepkit.render and
nepkit.convert; this module decides only where output goes and what exit code
to leave behind.

Notes
-----
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

import calendar
import json
import shlex
import sys
from collections.abc import Generator
from contextlib import contextmanager, suppress
from datetime import date, datetime
from enum import StrEnum
from importlib.metadata import version
from typing import Annotated, Any, Final, cast
from zoneinfo import ZoneInfo

import typer
from rich.console import Console
from rich.panel import Panel
from typer.main import get_command

from nepkit.calendar_data import MAX_BS_YEAR, MIN_BS_YEAR
from nepkit.convert import MAX_AD_DATE, MIN_AD_DATE, BSDate, ad_to_bs, bs_to_ad
from nepkit.exceptions import DateOutOfRangeError, InvalidDateError
from nepkit.render import (
    ACCENT,
    MonthGrid,
    ad_month_grid,
    block_width,
    bs_month_grid,
    bs_month_name,
    render_body_markup,
    render_plain,
    to_devnagari_numerals,
    weekday_name,
)

EXIT_INVALID_DATE: Final[int] = 3
EXIT_OUT_OF_RANGE: Final[int] = 4

_DATE_PARTS: Final[int] = 3

app = typer.Typer(
    name="nepkit",
    help="Bikram Sambat (BS) <-> Gregorian (AD) date conversion.",
    # Click's own setting, forwarded as-is: -h works everywhere --help does,
    # on the top-level app and every subcommand alike, not just here.
    context_settings={"help_option_names": ["-h", "--help"]},
)

# figlet "standard", composed glyph by glyph so the columns actually line up.
_ASCII_TITLE: Final[str] = r"""
                      _     _  _
 _ __    ___   _ __  | | __(_)| |_
| '_ \  / _ \ | '_ \ | |/ /| || __|
| | | ||  __/ | |_) ||   < | || |_
|_| |_| \___| | .__/ |_|\_\|_| \__|
              |_|"""

_PROMPT: Final[str] = "nepkit> "
_QUIT_WORDS: Final[frozenset[str]] = frozenset({"quit", "exit", "q"})
# Prompt-only words. They are not subcommands because they mean nothing outside
# a session -- `nepkit clear` should stay a usage error, not clear your screen.
_CLEAR_WORDS: Final[frozenset[str]] = frozenset({"clear", "cls"})
_HISTORY_LENGTH: Final[int] = 1000


class ColorMode(StrEnum):
    """When to dress up calendar output. Grids only; conversions are never coloured.

    Attributes
    ----------
    auto
        Colour only when stdout is a terminal.
    always
        Always colour, even when redirected.
    never
        Never colour.
    """

    auto = "auto"
    always = "always"
    never = "never"


class Script(StrEnum):
    """Which script to render human-readable dates in.

    Attributes
    ----------
    latin
        Romanised month names, ASCII digits (the current behaviour).
    devnagari
        Devnagari BS month names, Devnagari digits everywhere. Gregorian
        month names (e.g. "July") have no Devnagari table and are always
        Latin, whichever script is chosen.
    """

    latin = "latin"
    devnagari = "devnagari"


def _today() -> date:
    """Return today's date.

    Seam for tests. Patch this rather than the clock itself.

    Returns
    -------
    date
        Today's Gregorian date.
    """
    return date.today()


def _now_npt() -> datetime:
    """Return the current date and time in Nepal Standard Time, naive.

    Separate from `_today()`, and not built on top of it: the two commands
    that show a time (`today`, and the REPL banner) need their date and
    time to come from the same clock read, or the two could disagree by a
    few milliseconds at a day boundary. Everywhere else keeps using
    `_today()`, unaffected by this.

    Seam for tests. Patch this rather than the clock itself.

    Returns
    -------
    datetime.datetime
        The current NPT date and time, tzinfo stripped -- nepkit's
        conversion functions work only with naive NPT values.
    """
    return datetime.now(ZoneInfo("Asia/Kathmandu")).replace(tzinfo=None)


def _stdin_is_interactive() -> bool:
    """Report whether stdin is a live terminal.

    Seam for tests, and the guard that keeps `nepkit` usable in a pipeline.

    Returns
    -------
    bool
        True if stdin is a tty.
    """
    return sys.stdin.isatty()


def _enable_line_editing() -> bool:
    """Give input() cursor keys and history by importing readline.

    The import *is* the mechanism: readline hooks itself into input(), so
    Up/Down recall and Ctrl-A/Ctrl-E editing arrive without another line of
    code. It only engages on a real terminal, which is why no test can observe
    the recall itself.

    CPython ships no readline on Windows; pyreadline3 supplies one there (see
    the marker in pyproject.toml), which is why this needs no platform branch.
    The except clause still matters: pyreadline3 drives the Win32 console API
    and can fail where Python has no real console, and the prompt has to keep
    working when it does.

    Returns
    -------
    bool
        True if line editing was successfully enabled.
    """
    try:
        import readline
    except ImportError:
        return False
    except Exception:
        # pyreadline3 installs its Win32 console hook during import, so it can
        # fail with whatever the console layer raises rather than ImportError.
        # Line editing is a nicety; the prompt has to open either way.
        return False
    readline.set_history_length(_HISTORY_LENGTH)
    return True


def _dispatch(line: str) -> None:
    """Run one REPL line through the same command table the shell uses.

    standalone_mode=False makes Typer return the exit code instead of calling
    sys.exit, so a failing command ends the line rather than the session.

    Parameters
    ----------
    line : str
        One line of input, shell-split and dispatched as a `nepkit`
        invocation.
    """
    try:
        get_command(app).main(shlex.split(line), prog_name="nepkit", standalone_mode=False)
    except Exception as exc:
        # Deliberately broad. A typo must not throw the user out of the session,
        # and Typer's usage errors live in typer._click.exceptions -- a private
        # module this should not be importing to name them precisely.
        typer.echo(f"error: {exc}", err=True)


def _today_line() -> str:
    """Format today in both calendars, or a note that it is off the end of the table.

    Decorating the banner must never stop the session from opening, which it
    would once the clock passes MAX_AD_DATE in 2034.

    Returns
    -------
    str
        A rich-markup line for the REPL banner.
    """
    now = _now_npt()
    ad = now.date()
    day = weekday_name(ad)
    time_text = now.strftime("%H:%M")
    if not (MIN_AD_DATE <= ad <= MAX_AD_DATE):
        return (
            f"[dim]Today [/dim] {time_text} NPT  AD {_format_ad_named(ad)} {day}  "
            "[dim](outside the supported range)[/dim]"
        )
    return (
        f"[dim]Today [/dim] {time_text} NPT  "
        f"BS [bold]{_format_bs_named(ad_to_bs(ad))}[/bold]   AD {_format_ad_named(ad)} {day}"
    )


def _print_banner(*, editing: bool) -> None:
    """Print the ASCII wordmark, version, today's date, and usage hint.

    Parameters
    ----------
    editing : bool
        Whether line editing is active, to decide if the Up/Down hint is
        shown.
    """
    # A plain Console, not force_terminal: the REPL needs stdin to be a tty but
    # stdout can still be redirected, and then this should come out unstyled.
    console = Console()
    console.print(_ASCII_TITLE, style="bold cyan", markup=False, highlight=False)
    # Flush left, so the info block lines up with the wordmark's left edge.
    console.print(
        f"[bold]nepkit[/bold] [dim]v{version('nepkit')}[/dim] "
        f"[dim]-[/dim] Bikram Sambat (BS) <-> Gregorian (AD) date conversion",
        soft_wrap=True,
        highlight=False,
    )
    console.print(_today_line(), soft_wrap=True, highlight=False)
    hint = "  Up/Down recalls history." if editing else ""
    console.print(
        f"\n[dim]Type a command, 'help', 'clear', or 'quit'.{hint}[/dim]",
        soft_wrap=True,
        highlight=False,
    )
    console.print()


def _clear_screen() -> None:
    """Wipe the terminal.

    A no-op when stdout is redirected, so a session whose output is being
    captured never has escape sequences written into the capture.
    """
    Console().clear()


def _run_repl() -> None:
    """Run the interactive REPL until the user quits or sends EOF."""
    editing = _enable_line_editing()
    _clear_screen()
    _print_banner(editing=editing)
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
        word = line.lower()
        if word in _QUIT_WORDS:
            return
        if word in _CLEAR_WORDS:
            _clear_screen()
            _print_banner(editing=editing)
            continue
        _dispatch("--help" if word == "help" else line)


def _version_callback(show_version: bool) -> None:
    """Print the installed version and exit, if `show_version` is set.

    is_eager on the option that drives this means it fires before Typer
    parses anything else, so `nepkit --version` works even though no
    subcommand was given.

    Parameters
    ----------
    show_version : bool
        Whether `--version` was passed.

    Raises
    ------
    typer.Exit
        Always, when `show_version` is True -- printing the version is the
        entire command.
    """
    if show_version:
        typer.echo(f"nepkit {version('nepkit')}")
        raise typer.Exit()


VersionOption = Annotated[
    bool,
    typer.Option(
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
]


def _ensure_utf8_stdio() -> None:
    """Force stdout/stderr to UTF-8, in place of a Windows console's ANSI codepage.

    `today` defaults to `--script devnagari`, and every other command accepts
    it, so Devanagari output is no longer opt-in. `typer.echo` writes straight
    to `sys.stdout`, which on Windows defaults to the console's codepage
    (commonly cp1252) -- a stream that cannot encode Devanagari at all raises
    `UnicodeEncodeError` on the first such character. This has to run before
    anything is printed.
    """
    for stream in (sys.stdout, sys.stderr):
        # Not every stream supports reconfigure (some test doubles don't), and
        # a stream already mid-write cannot change encoding -- either way,
        # printing has to proceed rather than crash on the encoding fix itself.
        with suppress(AttributeError, ValueError, OSError):
            cast(Any, stream).reconfigure(encoding="utf-8")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, show_version: VersionOption = False) -> None:
    """Bikram Sambat <-> Gregorian date conversion.

    Parameters
    ----------
    ctx : typer.Context
        Typer's invocation context, used to detect whether a subcommand was
        given.
    show_version : bool, optional
        Whether `--version` was passed. Handled entirely by
        `_version_callback`; unused here beyond declaring the option.
    """
    _ensure_utf8_stdio()
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
    """Turn nepkit's date errors into stderr messages and distinct exit codes.

    Yields
    ------
    None
        Nothing; used only for its exception handling.

    Raises
    ------
    typer.Exit
        With `EXIT_INVALID_DATE` or `EXIT_OUT_OF_RANGE`, after printing the
        original error to stderr.
    """
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

    Parameters
    ----------
    text : str
        The date string to parse.

    Returns
    -------
    tuple of (int, int, int)
        The `(year, month, day)` parsed from `text`.

    Raises
    ------
    InvalidDateError
        If `text` is not in YYYY-MM-DD form.
    """
    parts = text.split("-")
    if len(parts) != _DATE_PARTS or not all(part.isdigit() for part in parts):
        raise InvalidDateError(f"{text!r} is not a date in YYYY-MM-DD form")
    year, month, day = (int(part) for part in parts)
    return year, month, day


def _parse_bs(text: str) -> BSDate:
    """Parse a Bikram Sambat date string.

    Parameters
    ----------
    text : str
        The date string, YYYY-MM-DD.

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
    year, month, day = _parse_ymd(text)
    return BSDate(year=year, month=month, day=day)  # validates against the table


def _parse_ad(text: str) -> date:
    """Parse a Gregorian date string.

    Parameters
    ----------
    text : str
        The date string, YYYY-MM-DD.

    Returns
    -------
    date
        The parsed Gregorian date.

    Raises
    ------
    InvalidDateError
        If `text` is not a real Gregorian date.
    """
    year, month, day = _parse_ymd(text)
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise InvalidDateError(f"AD {text} is not a real Gregorian date") from exc


def _format_bs(bs: BSDate, *, devnagari: bool = False) -> str:
    """Format a BSDate as zero-padded YYYY-MM-DD.

    Parameters
    ----------
    bs : BSDate
        The date to format.
    devnagari : bool, optional
        Render the digits in Devnagari. Default is False.

    Returns
    -------
    str
        The formatted date.
    """
    text = f"{bs.year:04d}-{bs.month:02d}-{bs.day:02d}"
    return to_devnagari_numerals(text) if devnagari else text


def _format_bs_named(bs: BSDate, *, devnagari: bool = False) -> str:
    """Format a BSDate as "day month year", e.g. "1 Baisakh 2083".

    Parameters
    ----------
    bs : BSDate
        The date to format.
    devnagari : bool, optional
        Render the month name and digits in Devnagari. Default is False.

    Returns
    -------
    str
        The formatted date.
    """
    text = f"{bs.day} {bs_month_name(bs.month, devnagari=devnagari)} {bs.year}"
    return to_devnagari_numerals(text) if devnagari else text


def _format_ad_named(ad: date) -> str:
    """Format an AD date as "day month year", e.g. "12 Aug 2026".

    Always Latin: there is no Devnagari table for Gregorian month names, so
    this ignores script choice the way the grid titles already do.

    Parameters
    ----------
    ad : date
        The date to format.

    Returns
    -------
    str
        The formatted date.
    """
    return f"{ad.day} {calendar.month_abbr[ad.month]} {ad.year}"


def _emit_grid(grid: MonthGrid, kind: str, *, as_json: bool, color: ColorMode) -> None:
    """Print a month grid as JSON, plain text, or a coloured panel.

    Parameters
    ----------
    grid : MonthGrid
        The grid to print.
    kind : str
        "bs" or "ad", included in the JSON output to identify the calendar.
    as_json : bool
        Whether to emit machine-readable JSON instead of a rendered grid.
    color : ColorMode
        When to colourise the grid; ignored when `as_json` is True.
    """
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
    width = block_width(grid)
    markup_body = render_body_markup(grid)
    body = f"[dim]{grid.subtitle.center(width)}[/dim]\n{markup_body}"
    Console(force_terminal=True).print(
        Panel.fit(body, title=f"[bold]{grid.title}[/bold]", border_style=ACCENT)
    )


JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
ColorOption = Annotated[ColorMode, typer.Option("--color", help="When to colourise the grid.")]
ScriptOption = Annotated[
    Script,
    typer.Option("--script", help="Script for human-readable dates. Ignored with --json."),
]
YearArg = Annotated[int | None, typer.Argument(help="Year. Defaults to the current one.")]
MonthArg = Annotated[int | None, typer.Argument(help="Month, 1-12. Defaults to the current one.")]


@app.command("bs2ad", help="Convert a Bikram Sambat date to Gregorian.")
def bs_to_ad_command(
    bs_date: Annotated[str, typer.Argument(metavar="BS_DATE", help="Bikram Sambat YYYY-MM-DD.")],
    as_json: JsonOption = False,
    script: ScriptOption = Script.latin,
) -> None:
    """Convert a Bikram Sambat date to Gregorian.

    Parameters
    ----------
    bs_date : str
        The Bikram Sambat date, YYYY-MM-DD.
    as_json : bool, optional
        Emit machine-readable JSON instead of plain text. Default is False.
    script : Script, optional
        Script for the printed date. Ignored when `as_json` is True.
        Default is `Script.latin`.
    """
    with _reported_as_exit_code():
        bs = _parse_bs(bs_date)
        ad = bs_to_ad(bs)
    if as_json:
        typer.echo(
            json.dumps({"bs": _format_bs(bs), "ad": ad.isoformat(), "weekday": weekday_name(ad)})
        )
        return
    devnagari = script is Script.devnagari
    ad_text = to_devnagari_numerals(ad.isoformat()) if devnagari else ad.isoformat()
    typer.echo(f"{ad_text} {weekday_name(ad, devnagari=devnagari)}")


@app.command("ad2bs", help="Convert a Gregorian date to Bikram Sambat.")
def ad_to_bs_command(
    ad_date: Annotated[str, typer.Argument(metavar="AD_DATE", help="Gregorian YYYY-MM-DD.")],
    as_json: JsonOption = False,
    script: ScriptOption = Script.latin,
) -> None:
    """Convert a Gregorian date to Bikram Sambat.

    Parameters
    ----------
    ad_date : str
        The Gregorian date, YYYY-MM-DD.
    as_json : bool, optional
        Emit machine-readable JSON instead of plain text. Default is False.
    script : Script, optional
        Script for the printed date. Ignored when `as_json` is True.
        Default is `Script.latin`.
    """
    with _reported_as_exit_code():
        ad = _parse_ad(ad_date)
        bs = ad_to_bs(ad)
    if as_json:
        typer.echo(
            json.dumps({"bs": _format_bs(bs), "ad": ad.isoformat(), "weekday": weekday_name(ad)})
        )
        return
    devnagari = script is Script.devnagari
    typer.echo(f"{_format_bs(bs, devnagari=devnagari)} {weekday_name(ad, devnagari=devnagari)}")


@app.command("today", help="Print today's date in both calendars.")
def today_command(as_json: JsonOption = False, script: ScriptOption = Script.devnagari) -> None:
    """Print today's date in both calendars.

    The plain-text lines use named dates, e.g. "BS 1 Baisakh 2083" and
    "AD 12 Aug 2026". JSON keeps the numeric "bs"/"ad" fields for machine
    consumption and adds "bs_text"/"ad_text" alongside them with the same
    named form shown in plain text.

    Parameters
    ----------
    as_json : bool, optional
        Emit machine-readable JSON instead of plain text. Default is False.
    script : Script, optional
        Script for the printed dates. Ignored when `as_json` is True.
        Default is `Script.devnagari`, unlike `bs2ad`/`ad2bs`/`range`, which
        default to `Script.latin`.
    """
    now = _now_npt()
    ad = now.date()
    with _reported_as_exit_code():
        bs = ad_to_bs(ad)
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "bs": _format_bs(bs),
                    "bs_text": _format_bs_named(bs),
                    "ad": ad.isoformat(),
                    "ad_text": _format_ad_named(ad),
                    "time": now.strftime("%H:%M:%S"),
                    "weekday": weekday_name(ad),
                }
            )
        )
        return
    devnagari = script is Script.devnagari
    time_text = now.strftime("%H:%M")
    ad_time_text, ad_day = time_text, weekday_name(ad)
    bs_time_text = to_devnagari_numerals(time_text) if devnagari else time_text
    bs_day = weekday_name(ad, devnagari=devnagari)
    # Two labelled lines, the same shape `range` prints, so the two commands
    # that report a position in both calendars read alike. --script only ever
    # touches the BS line: there is no Devnagari table for Gregorian month
    # names, so AD's date, time, and weekday stay Latin regardless of script,
    # the same rule the grid titles already follow.
    typer.echo(f"BS {_format_bs_named(bs, devnagari=devnagari)} {bs_time_text} {bs_day}")
    typer.echo(f"AD {_format_ad_named(ad)} {ad_time_text} {ad_day}")


@app.command("range", help="Print the date range nepkit has data for.")
def range_command(as_json: JsonOption = False, script: ScriptOption = Script.latin) -> None:
    """Print the date range nepkit has data for.

    Parameters
    ----------
    as_json : bool, optional
        Emit machine-readable JSON instead of plain text. Default is False.
    script : Script, optional
        Script for the printed range. Ignored when `as_json` is True.
        Default is `Script.latin`.
    """
    bs_min, bs_max = f"{MIN_BS_YEAR:04d}-01-01", _format_bs(ad_to_bs(MAX_AD_DATE))
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "bs": {"min": bs_min, "max": bs_max},
                    "ad": {
                        "min": MIN_AD_DATE.isoformat(),
                        "max": MAX_AD_DATE.isoformat(),
                    },
                }
            )
        )
        return
    devnagari = script is Script.devnagari
    years = f"{MIN_BS_YEAR}-{MAX_BS_YEAR}"
    ad_min, ad_max = MIN_AD_DATE.isoformat(), MAX_AD_DATE.isoformat()
    if devnagari:
        bs_min, bs_max = to_devnagari_numerals(bs_min), to_devnagari_numerals(bs_max)
        years = to_devnagari_numerals(years)
        ad_min, ad_max = to_devnagari_numerals(ad_min), to_devnagari_numerals(ad_max)
    typer.echo(f"BS {bs_min} .. {bs_max}  (years {years})")
    typer.echo(f"AD {ad_min} .. {ad_max}")


@app.command("calbs", help="Display a Bikram Sambat month.")
def calbs_command(
    year: YearArg = None,
    month: MonthArg = None,
    as_json: JsonOption = False,
    color: ColorOption = ColorMode.auto,
) -> None:
    """Display a Bikram Sambat month.

    Parameters
    ----------
    year : int or None, optional
        The BS year. Defaults to the current one.
    month : int or None, optional
        The BS month, 1-12. Defaults to the current one.
    as_json : bool, optional
        Emit machine-readable JSON instead of a rendered grid. Default is
        False.
    color : ColorMode, optional
        When to colourise the grid. Default is `ColorMode.auto`.
    """
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


@app.command("calad", help="Display a Gregorian month.")
def calad_command(
    year: YearArg = None,
    month: MonthArg = None,
    as_json: JsonOption = False,
    color: ColorOption = ColorMode.auto,
) -> None:
    """Display a Gregorian month.

    Parameters
    ----------
    year : int or None, optional
        The Gregorian year. Defaults to the current one.
    month : int or None, optional
        The Gregorian month, 1-12. Defaults to the current one.
    as_json : bool, optional
        Emit machine-readable JSON instead of a rendered grid. Default is
        False.
    color : ColorMode, optional
        When to colourise the grid. Default is `ColorMode.auto`.
    """
    with _reported_as_exit_code():
        today = _today()
        grid = ad_month_grid(year or today.year, month or today.month, today=today)
    _emit_grid(grid, "ad", as_json=as_json, color=color)
