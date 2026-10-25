"""Detection defaults and how an isatty answer is read."""

from __future__ import annotations

import io
import sys

import pytest

from osc8link import auto_link, link, supports_hyperlinks


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


class EmptyTty(Tty):
    """A terminal stream that is falsy, as a container with nothing in it is."""

    def __len__(self) -> int:
        return 0


def test_a_falsy_stream_is_used_not_replaced_by_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only None picks sys.stdout: a stream given is read even when its truth value is False.
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "platform", "linux")
    for name in ("FORCE_HYPERLINK", "FORCE_COLOR", "CI", "TEAMCITY_VERSION", "WT_SESSION", "TERM"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "ghostty")
    stream = EmptyTty()
    assert not stream
    assert supports_hyperlinks(stream, env={"TERM_PROGRAM": "ghostty"}, platform="linux") is True
    assert auto_link("https://a.test", "A", stream=stream) == link("https://a.test", "A")


class Interrupted:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def isatty(self) -> bool:
        raise self.error


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(1)])
def test_an_interrupt_inside_isatty_is_not_swallowed(error: BaseException) -> None:
    # Only an Exception subclass means "not a terminal"; Ctrl-C and exit still propagate.
    with pytest.raises(type(error)):
        supports_hyperlinks(Interrupted(error), env={"TERM_PROGRAM": "ghostty"}, platform="linux")
