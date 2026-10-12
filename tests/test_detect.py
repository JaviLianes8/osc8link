"""Terminal detection.

Written by hand from the rules of the supports-hyperlinks package (chalk, index.js at commit
164e9f1f7f412715830db9d849275cd99b0ea135, read 2026-10-12) and the TERM values of the
terminals in the OSC 8 adoption list (Alhadis/OSC8-Adoption at 2bb57119a930).
"""

from __future__ import annotations

import io

import pytest

from osc8link import supports_hyperlinks


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def check(env: dict[str, str], *, tty: bool = True, platform: str = "linux") -> bool:
    stream = Tty() if tty else io.StringIO()
    return supports_hyperlinks(stream, env=env, platform=platform)


@pytest.mark.parametrize(
    "env",
    [
        {"WT_SESSION": ""},
        {"TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "3.1.0"},
        {"TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "4.0"},
        {"TERM_PROGRAM": "WezTerm", "TERM_PROGRAM_VERSION": "20240203-110809-5046fc22"},
        {"TERM_PROGRAM": "WezTerm", "TERM_PROGRAM_VERSION": "0-unstable-2021-01-01"},
        {"TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "1.72.0"},
        {"TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "2.0.1"},
        {"TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "0.42.0", "CURSOR_TRACE_ID": "x"},
        {"TERM_PROGRAM": "ghostty"},
        {"TERM_PROGRAM": "zed"},
        {"TERM_PROGRAM": "WarpTerminal"},
        {"TERM_PROGRAM": "Orca"},
        {"VTE_VERSION": "5001"},
        {"VTE_VERSION": "7600"},
        {"VTE_VERSION": "0.52.2"},
        {"TERM": "alacritty"},
        {"TERM": "xterm-kitty"},
        {"TERM": "foot"},
        {"TERM": "xterm-ghostty"},
        {"TERM_PROGRAM": "tmux", "TERM": "xterm-kitty"},
    ],
)
def test_known_terminals_are_recognised(env: dict[str, str]) -> None:
    assert check(env) is True


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"TERM": "xterm-256color"},
        {"TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "3.0.9"},
        {"TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "2.9"},
        {"TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "nightly"},
        {"TERM_PROGRAM": "WezTerm", "TERM_PROGRAM_VERSION": "20200619-000000-x"},
        {"TERM_PROGRAM": "WezTerm", "TERM_PROGRAM_VERSION": "0-unstable-2020-06-19"},
        {"TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "1.71.2"},
        {"TERM_PROGRAM": "Apple_Terminal", "TERM_PROGRAM_VERSION": "455"},
        {"VTE_VERSION": "5000"},
        {"VTE_VERSION": "0.50.0"},
        {"VTE_VERSION": "4803"},
        {"TERM_PROGRAM": "ghostty", "CI": "true"},
        {"TERM_PROGRAM": "ghostty", "TEAMCITY_VERSION": "2024.1"},
        {"TERM_PROGRAM": "ghostty", "TERM": "dumb"},
        {"TERM_PROGRAM": "ghostty", "FORCE_COLOR": "0"},
        {"TERM_PROGRAM": "ghostty", "FORCE_COLOR": "false"},
    ],
)
def test_unknown_or_disabled_terminals_are_not(env: dict[str, str]) -> None:
    assert check(env) is False


def test_an_unknown_program_falls_back_to_vte_and_term() -> None:
    assert check({"TERM_PROGRAM": "other", "VTE_VERSION": "6003"}) is True


def test_a_pipe_never_shows_links() -> None:
    assert check({"TERM_PROGRAM": "ghostty"}, tty=False) is False
    assert check({"WT_SESSION": "1"}, tty=False) is False


def test_windows_needs_windows_terminal() -> None:
    assert (
        check({"TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "1.90.0"}, platform="win32")
        is False
    )
    assert check({"WT_SESSION": "abc"}, platform="win32") is True


@pytest.mark.parametrize(
    ("value", "expected"), [("1", True), ("true", True), ("0", False), ("00", False)]
)
def test_force_hyperlink_overrides_everything(value: str, expected: bool) -> None:
    assert check({"FORCE_HYPERLINK": value}, tty=False) is expected
    assert check({"FORCE_HYPERLINK": value, "TERM": "dumb", "CI": "1"}) is expected


def test_an_empty_force_hyperlink_is_ignored() -> None:
    assert check({"FORCE_HYPERLINK": "", "TERM": "alacritty"}) is True
    assert check({"FORCE_HYPERLINK": ""}, tty=False) is False


def test_streams_without_isatty_or_closed_are_not_terminals() -> None:
    closed = io.StringIO()
    closed.close()
    env = {"TERM_PROGRAM": "ghostty"}
    assert supports_hyperlinks(closed, env=env, platform="linux") is False
    assert supports_hyperlinks(object(), env=env, platform="linux") is False  # type: ignore[arg-type]


def test_defaults_read_stdout_and_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_HYPERLINK", "1")
    assert supports_hyperlinks() is True
    monkeypatch.setenv("FORCE_HYPERLINK", "0")
    assert supports_hyperlinks() is False
    monkeypatch.delenv("FORCE_HYPERLINK")
    monkeypatch.setattr("sys.stdout", None)
    assert supports_hyperlinks(env={"TERM": "alacritty"}, platform="linux") is False
