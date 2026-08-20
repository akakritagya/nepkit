"""The CLI's contract: exit codes, stream discipline, and machine-readable output.

The contract these tests pin down:

* stdout carries results and nothing else; stderr carries errors and nothing
  else. Neither ever carries both.
* Exit codes come straight from the exception hierarchy, so a caller can tell
  "that is not a date" (3) from "that is a date I have no data for" (4)
  without parsing any text.
* stdout never contains ANSI escapes unless colour was explicitly demanded.
"""

import builtins
import json
import re
from datetime import date
from importlib.metadata import version

import pytest
from typer.testing import CliRunner

from nepkit import cli

runner = CliRunner()


def test_bs2ad_prints_the_converted_date_then_its_weekday() -> None:
    # The date still starts the line, so anything already cutting the first
    # field keeps working; the weekday is appended, never prepended.
    result = runner.invoke(cli.app, ["bs2ad", "2081-04-15"])
    assert result.exit_code == 0
    assert result.stdout == "2024-07-30 Tue\n"
    assert result.stderr == ""


def test_ad2bs_prints_the_converted_date_then_its_weekday() -> None:
    result = runner.invoke(cli.app, ["ad2bs", "2024-07-30"])
    assert result.exit_code == 0
    assert result.stdout == "2081-04-15 Tue\n"
    assert result.stderr == ""


def test_ad2bs_agrees_with_a_tier_three_oracle_pair() -> None:
    # Nepal declared a federal republic on 28 May 2008 = BS 2065-02-15, a
    # Wednesday -- the weekday is an independent check on the same record.
    result = runner.invoke(cli.app, ["ad2bs", "2008-05-28"])
    assert result.stdout == "2065-02-15 Wed\n"


@pytest.mark.parametrize(
    ("command", "argument"),
    [("bs2ad", "2081-13-01"), ("bs2ad", "2081-04-33"), ("ad2bs", "2024-13-01")],
    ids=["bs_month_13", "bs_day_33", "ad_month_13"],
)
def test_an_impossible_date_exits_3_and_says_so_on_stderr(command: str, argument: str) -> None:
    result = runner.invoke(cli.app, [command, argument])
    assert result.exit_code == 3
    assert result.stdout == ""
    assert result.stderr.strip()


@pytest.mark.parametrize(
    ("command", "argument"),
    [("bs2ad", "2095-01-01"), ("ad2bs", "2040-01-01")],
    ids=["bs_year_past_table", "ad_year_past_window"],
)
def test_a_real_date_outside_the_range_exits_4(command: str, argument: str) -> None:
    result = runner.invoke(cli.app, [command, argument])
    assert result.exit_code == 4
    assert result.stdout == ""
    assert result.stderr.strip()


def test_malformed_input_exits_the_same_way_in_both_directions() -> None:
    """The same user mistake must not depend on which direction they asked for.

    Typer could parse the AD side natively, which would exit 2 there and 3 on
    the BS side for identical garbage. Both are parsed by nepkit instead.
    """
    bs = runner.invoke(cli.app, ["bs2ad", "not-a-date"])
    ad = runner.invoke(cli.app, ["ad2bs", "not-a-date"])
    assert bs.exit_code == ad.exit_code == 3


def test_version_flag_prints_the_version_and_exits_0() -> None:
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert version("nepkit") in result.stdout


def test_bare_invocation_without_a_terminal_still_prints_help_and_exits_2() -> None:
    """A pipeline must never get an interactive prompt.

    Without this guard `nepkit` in a script would block on stdin forever, or
    silently eat whatever was being piped into it.
    """
    result = runner.invoke(cli.app, [])
    assert result.exit_code == 2
    assert "Usage:" in result.stdout


def test_bare_invocation_on_a_terminal_starts_a_repl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    result = runner.invoke(cli.app, [], input="today\nbs2ad 2081-04-15\nquit\n")
    assert result.exit_code == 0
    assert "BS 2081-04-15" in result.stdout  # today
    assert "2024-07-30" in result.stdout  # the conversion


def test_the_repl_opens_with_an_ascii_title_and_app_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    out = runner.invoke(cli.app, [], input="quit\n").stdout

    assert "|_| |_|" in out, "the ascii title is missing"
    assert version("nepkit") in out
    assert "Bikram Sambat" in out
    assert "BS 2081-04-15" in out and "AD 2024-07-30" in out, "today is not shown"


def test_the_banner_survives_a_clock_outside_the_supported_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After 2034-04-13 there is no BS date for today, and the banner still has to open.

    Reading the clock to decorate a banner must never be able to stop the REPL
    from starting.
    """
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_today", lambda: date(2040, 1, 1))
    result = runner.invoke(cli.app, [], input="bs2ad 2081-04-15\nquit\n")
    assert result.exit_code == 0
    assert "|_| |_|" in result.stdout
    assert "2024-07-30" in result.stdout, "the session did not work"


def test_the_repl_wipes_the_screen_before_drawing_the_banner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wipes: list[int] = []
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_clear_screen", lambda: wipes.append(1))
    runner.invoke(cli.app, [], input="quit\n")
    assert len(wipes) == 1, "the screen was not wiped on startup"


def test_clear_goes_through_the_same_screen_wipe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Startup and `clear` should not drift into two different ways of doing this."""
    wipes: list[int] = []
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_clear_screen", lambda: wipes.append(1))
    runner.invoke(cli.app, [], input="clear\nquit\n")
    assert len(wipes) == 2


@pytest.mark.parametrize("word", ["clear", "cls", "CLEAR"], ids=["clear", "cls", "uppercase"])
def test_clear_redraws_the_banner(monkeypatch: pytest.MonkeyPatch, word: str) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    out = runner.invoke(cli.app, [], input=f"{word}\nquit\n").stdout
    # Once at startup, once after clearing.
    assert out.count("|_| |_|") == 2, "the banner was not redrawn"
    assert out.count("Today ") == 2, "the info block was not redrawn with it"


def test_clear_does_not_end_the_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    result = runner.invoke(cli.app, [], input="clear\nbs2ad 2081-04-15\nquit\n")
    assert result.exit_code == 0
    assert "2024-07-30" in result.stdout


def test_clear_is_advertised_in_the_banner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    out = runner.invoke(cli.app, [], input="quit\n").stdout
    assert "'clear'" in out


def test_clear_is_not_a_shell_subcommand() -> None:
    """It only means anything at the prompt, so it must not appear as a verb."""
    assert runner.invoke(cli.app, ["clear"]).exit_code == 2


def test_line_editing_is_available_on_this_platform() -> None:
    """Every platform now has a readline: CPython's, or pyreadline3 on Windows.

    This is the assertion that pins the pyreadline3 dependency in place. If the
    marker in pyproject.toml stops matching, or pyreadline3 stops hooking
    PyOS_ReadlineFunctionPointer on a Python we support, the Windows job fails
    here rather than shipping a REPL whose Up/Down key silently does nothing.
    """
    assert cli._enable_line_editing() is True


def test_line_editing_survives_a_readline_that_explodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing readline must cost the editing keys, not the prompt.

    pyreadline3 installs its console hook during import, so it can raise
    something other than ImportError -- catching only that would turn a missing
    nicety into a REPL that will not open at all.
    """
    real_import = builtins.__import__

    def explode(name: str, *args: object, **kwargs: object) -> object:
        if name == "readline":
            raise RuntimeError("no console handle")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", explode)
    assert cli._enable_line_editing() is False


def test_the_banner_advertises_history_when_line_editing_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_enable_line_editing", lambda: True)
    result = runner.invoke(cli.app, [], input="quit\n")
    assert "Up/Down" in result.stdout


def test_the_repl_still_works_without_readline(monkeypatch: pytest.MonkeyPatch) -> None:
    """readline can still fail to load. The prompt must degrade, not fail.

    pyreadline3 covers Windows now, but it drives the Win32 console API and can
    decline to install its hook -- under a terminal that gives Python no real
    console, for one. Nothing about dispatch depends on line editing, so losing
    it should cost the history hint and nothing else.
    """
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_enable_line_editing", lambda: False)
    result = runner.invoke(cli.app, [], input="bs2ad 2081-04-15\nquit\n")
    assert result.exit_code == 0
    assert "2024-07-30" in result.stdout
    assert "Up/Down" not in result.stdout


@pytest.mark.parametrize("word", ["quit", "exit", "q"], ids=["quit", "exit", "q"])
def test_the_repl_leaves_on_any_quit_word(monkeypatch: pytest.MonkeyPatch, word: str) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    assert runner.invoke(cli.app, [], input=f"{word}\n").exit_code == 0


def test_the_repl_leaves_cleanly_on_end_of_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl-D should end the session, not raise EOFError at the user."""
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    result = runner.invoke(cli.app, [], input="")
    assert result.exit_code == 0
    assert "Traceback" not in result.stdout


@pytest.mark.parametrize(
    "bad_line",
    ["nosuchcommand", "bs2ad 2095-01-01", "bs2ad not-a-date", "bs2ad", "bs2ad --bogus"],
    ids=["unknown_verb", "out_of_range", "malformed", "missing_argument", "unknown_flag"],
)
def test_a_bad_line_does_not_end_the_repl_session(
    monkeypatch: pytest.MonkeyPatch, bad_line: str
) -> None:
    """A typo must not throw the user out of the session."""
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    result = runner.invoke(cli.app, [], input=f"{bad_line}\nbs2ad 2081-04-15\nquit\n")
    assert result.exit_code == 0
    assert "2024-07-30" in result.stdout, "the command after the bad line never ran"


def test_blank_lines_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    result = runner.invoke(cli.app, [], input="\n\n   \nbs2ad 2081-04-15\nquit\n")
    assert result.exit_code == 0
    assert "2024-07-30" in result.stdout


def test_an_unknown_command_exits_2_as_a_usage_error() -> None:
    result = runner.invoke(cli.app, ["nosuchcommand"])
    assert result.exit_code == 2


def test_help_exits_zero() -> None:
    assert runner.invoke(cli.app, ["--help"]).exit_code == 0


@pytest.mark.parametrize(
    ("command", "argument"),
    [("bs2ad", "2081-04-15"), ("ad2bs", "2024-07-30")],
    ids=["bs2ad", "ad2bs"],
)
def test_json_output_carries_both_calendars(command: str, argument: str) -> None:
    result = runner.invoke(cli.app, [command, argument, "--json"])
    assert result.exit_code == 0
    # 2024-07-30 is a Tuesday, and BS 2081-04-15 is the same physical day, so
    # one weekday describes both calendars rather than one per calendar.
    assert json.loads(result.stdout) == {
        "bs": "2081-04-15",
        "ad": "2024-07-30",
        "weekday": "Tue",
    }


def test_today_uses_the_injectable_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without this seam the suite would be time-dependent, and would start
    # failing for real once the clock passes the end of the table in 2034.
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    result = runner.invoke(cli.app, ["today"])
    assert result.exit_code == 0
    # Two labelled lines, matching `range`: both commands answer "where are we
    # in each calendar?" and should not be formatted differently. The weekday
    # repeats on both because they are one day -- each line stays readable on
    # its own rather than sending you to the other for half the answer.
    assert result.stdout == "BS 2081-04-15 Tue\nAD 2024-07-30 Tue\n"


def test_today_json_carries_both_calendars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    result = runner.invoke(cli.app, ["today", "--json"])
    assert json.loads(result.stdout) == {
        "bs": "2081-04-15",
        "ad": "2024-07-30",
        "weekday": "Tue",
    }


def test_today_exits_4_when_the_clock_is_outside_the_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2040, 1, 1))
    result = runner.invoke(cli.app, ["today"])
    assert result.exit_code == 4
    assert result.stdout == ""


def test_range_reports_both_supported_windows() -> None:
    result = runner.invoke(cli.app, ["range", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "bs": {"min": "2000-01-01", "max": "2090-12-30"},
        "ad": {"min": "1943-04-14", "max": "2034-04-13"},
    }


def test_calbs_renders_the_month_grid() -> None:
    result = runner.invoke(cli.app, ["calbs", "2081", "4"])
    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    assert lines[0].strip() == "Shrawan 2081"
    assert lines[2] == "Sun Mon Tue Wed Thu Fri Sat"
    assert lines[3] == "          1   2   3   4   5"


def test_calad_renders_the_month_grid() -> None:
    result = runner.invoke(cli.app, ["calad", "2024", "7"])
    assert result.exit_code == 0
    assert result.stdout.splitlines()[0].strip() == "July 2024"


def test_cal_defaults_to_the_current_month(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    assert runner.invoke(cli.app, ["calbs"]).stdout.splitlines()[0].strip() == "Shrawan 2081"
    assert runner.invoke(cli.app, ["calad"]).stdout.splitlines()[0].strip() == "July 2024"


def test_piped_output_is_free_of_ansi_escapes() -> None:
    # CliRunner is never a terminal, so this is exactly what a pipe would see.
    result = runner.invoke(cli.app, ["calbs", "2081", "4"])
    assert "\x1b[" not in result.stdout


def test_colour_can_be_forced_on_and_off() -> None:
    forced = runner.invoke(cli.app, ["calbs", "2081", "4", "--color", "always"])
    never = runner.invoke(cli.app, ["calbs", "2081", "4", "--color", "never"])
    assert forced.exit_code == never.exit_code == 0
    # Forced output is boxed *and* styled; --color never must be neither, since
    # that is what anything downstream of a pipe has to be able to parse.
    # Test the side rather than a corner: Rich draws a legacy-safe box on
    # Windows (┌ square) and a rounded one (╭) elsewhere, but │ is common to
    # both, and "is there a box at all" is the actual claim here.
    assert "\x1b[" in forced.stdout
    assert "│" in forced.stdout
    assert "\x1b[" not in never.stdout
    assert "│" not in never.stdout


def test_todays_cell_is_highlighted_when_colour_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))  # = BS 2081-04-15
    out = runner.invoke(cli.app, ["calbs", "2081", "4", "--color", "always"]).stdout
    assert re.search(r"\x1b\[[0-9;]*m 15\x1b\[0m", out), "today's cell is not wrapped in a style"
    assert len(re.findall(r"\x1b\[[0-9;]*m 1[0-9]\x1b\[0m", out)) == 1, "more than one day styled"


def test_a_month_without_today_in_it_highlights_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    out = runner.invoke(cli.app, ["calbs", "2081", "6", "--color", "always"]).stdout
    assert not re.search(r"\x1b\[[0-9;]*m *\d+\x1b\[0m", out)


def test_plain_output_is_identical_whether_or_not_today_is_in_the_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A marker appearing for one day a month would break anything parsing stdout."""
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))  # inside Shrawan 2081
    inside = runner.invoke(cli.app, ["calbs", "2081", "4"]).stdout
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 1, 1))  # outside it
    outside = runner.invoke(cli.app, ["calbs", "2081", "4"]).stdout
    assert inside == outside
    assert "\x1b[" not in inside


def test_calbs_json_reports_which_day_is_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))

    def today_field(year: str, month: str) -> object:
        result = runner.invoke(cli.app, ["calbs", year, month, "--json"])
        return json.loads(result.stdout)["today"]

    assert today_field("2081", "4") == 15  # today is Shrawan 15
    assert today_field("2081", "6") is None


def test_the_coloured_panel_does_not_truncate_a_long_subtitle() -> None:
    """A subtitle wider than the grid used to get clipped by the panel border.

    'Ashadh 17 - Shrawan 16, 2081' is 28 characters against a 27-wide grid, so
    rendering it as panel furniture silently ate the year.
    """
    out = runner.invoke(cli.app, ["calad", "2024", "7", "--color", "always"]).stdout
    assert "Ashadh 17 - Shrawan 16, 2081" in re.sub(r"\x1b\[[0-9;]*m", "", out)


def test_calbs_json_describes_the_grid_without_drawing_it() -> None:
    result = runner.invoke(cli.app, ["calbs", "2081", "4", "--json"])
    payload = json.loads(result.stdout)
    assert payload["calendar"] == "bs"
    assert payload["title"] == "Shrawan 2081"
    assert payload["weeks"][0] == [None, None, 1, 2, 3, 4, 5]


def test_calbs_exits_4_for_a_year_outside_the_table() -> None:
    result = runner.invoke(cli.app, ["calbs", "2095", "1"])
    assert result.exit_code == 4
    assert result.stdout == ""


def test_calad_exits_4_for_a_month_it_cannot_fully_convert() -> None:
    result = runner.invoke(cli.app, ["calad", "2034", "4"])
    assert result.exit_code == 4
