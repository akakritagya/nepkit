"""The CLI's contract: exit codes, stream discipline, and machine-readable output.

The contract these tests pin down:

* stdout carries results and nothing else; stderr carries errors and nothing
  else. Neither ever carries both.
* Exit codes come straight from the exception hierarchy, so a caller can tell
  "that is not a date" (3) from "that is a date I have no data for" (4)
  without parsing any text.
* stdout never contains ANSI escapes unless colour was explicitly demanded.
"""

import json
from datetime import date

import pytest
from typer.testing import CliRunner

from nepkit import cli

runner = CliRunner()


def test_bs2ad_prints_only_the_converted_date() -> None:
    result = runner.invoke(cli.app, ["bs2ad", "2081-04-15"])
    assert result.exit_code == 0
    assert result.stdout == "2024-07-30\n"
    assert result.stderr == ""


def test_ad2bs_prints_only_the_converted_date() -> None:
    result = runner.invoke(cli.app, ["ad2bs", "2024-07-30"])
    assert result.exit_code == 0
    assert result.stdout == "2081-04-15\n"
    assert result.stderr == ""


def test_ad2bs_agrees_with_a_tier_three_oracle_pair() -> None:
    # Nepal declared a federal republic on 28 May 2008 = BS 2065-02-15.
    result = runner.invoke(cli.app, ["ad2bs", "2008-05-28"])
    assert result.stdout == "2065-02-15\n"


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
    assert json.loads(result.stdout) == {"bs": "2081-04-15", "ad": "2024-07-30"}


def test_today_uses_the_injectable_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without this seam the suite would be time-dependent, and would start
    # failing for real once the clock passes the end of the table in 2034.
    monkeypatch.setattr(cli, "_today", lambda: date(2024, 7, 30))
    result = runner.invoke(cli.app, ["today"])
    assert result.exit_code == 0
    assert result.stdout == "2081-04-15\n"


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
    assert "\x1b[" in forced.stdout
    assert "╭" in forced.stdout
    assert "\x1b[" not in never.stdout
    assert "╭" not in never.stdout


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
