"""Detection defaults and how an isatty answer is read."""

from __future__ import annotations

import io
import sys

import pytest

from osc8link import supports_hyperlinks


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


class Answer:
    """A stream whose isatty returns a value that is not a bool."""

    def __init__(self, value: object) -> None:
        self.value = value

    def isatty(self) -> bool:
        return self.value  # type: ignore[return-value]


@pytest.mark.parametrize(("platform", "expected"), [("win32", False), ("linux", True)])
def test_the_platform_defaults_to_sys_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str, expected: bool
) -> None:
    # The same terminal says no on a Windows console without WT_SESSION and yes elsewhere.
    monkeypatch.setattr(sys, "platform", platform)
    assert supports_hyperlinks(Tty(), env={"TERM_PROGRAM": "ghostty"}) is expected
    assert supports_hyperlinks(Tty(), env={"TERM_PROGRAM": "ghostty"}, platform=None) is expected


@pytest.mark.parametrize(("value", "expected"), [(1, True), ("yes", True), (0, False), ("", False)])
def test_isatty_is_read_by_its_truth_value(value: object, expected: bool) -> None:
    env = {"TERM_PROGRAM": "ghostty"}
    assert supports_hyperlinks(Answer(value), env=env, platform="linux") is expected
