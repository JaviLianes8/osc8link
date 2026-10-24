"""The documented differences from supports-hyperlinks, pinned one by one.

Written by hand. test_oracle_detect.py compares everything else with the package itself.
"""

from __future__ import annotations

import io
import sys

import pytest

from osc8link import supports_hyperlinks


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def check(env: dict[str, str]) -> bool:
    return supports_hyperlinks(Tty(), env=env, platform="linux")


def test_command_line_flags_are_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prog", "--no-hyperlink", "--hyperlink=never"])
    assert check({"TERM_PROGRAM": "ghostty"}) is True
    monkeypatch.setattr(sys, "argv", ["prog", "--hyperlink=always"])
    assert check({"TERM": "xterm-256color"}) is False


def test_netlify_is_not_special() -> None:
    assert check({"NETLIFY": "true"}) is False


def test_vte_5000_says_no_in_both_spellings() -> None:
    assert check({"VTE_VERSION": "5000"}) is False
    assert check({"VTE_VERSION": "0.50.0"}) is False
    assert check({"VTE_VERSION": "5001"}) is True


@pytest.mark.parametrize("term", ["foot", "foot-extra", "xterm-ghostty", "wezterm"])
def test_terms_from_the_adoption_list_say_yes(term: str) -> None:
    assert check({"TERM": term}) is True


def test_term_dumb_says_no_even_with_colour_forced() -> None:
    assert check({"TERM": "dumb", "FORCE_COLOR": "1", "TERM_PROGRAM": "ghostty"}) is False


def test_no_colour_level_is_required() -> None:
    # supports-color gives no colour without TERM or COLORTERM, so the package says no here.
    assert check({"TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "1.80.0"}) is True


@pytest.mark.parametrize(("value", "expected"), [("0", False), ("00", False), (" 0", False)])
def test_force_color_reads_a_leading_zero_as_off(value: str, expected: bool) -> None:
    assert check({"FORCE_COLOR": value, "TERM_PROGRAM": "ghostty"}) is expected


@pytest.mark.parametrize("value", ["", "1", "3", "true", "-1", "abc"])
def test_other_force_color_values_leave_detection_on(value: str) -> None:
    assert check({"FORCE_COLOR": value, "TERM_PROGRAM": "ghostty"}) is True
