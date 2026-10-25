"""Detection defaults and how an isatty answer is read."""

from __future__ import annotations

import collections
import io
import os
import sys
import types
from collections.abc import Callable
from typing import Any

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


class NotAMapping:
    """Has items() like a dict but is not a Mapping."""

    def items(self) -> list[tuple[str, str]]:
        return [("FORCE_HYPERLINK", "1")]


@pytest.mark.parametrize(
    ("env", "kind"),
    [
        (5, "int"),
        ("FORCE_HYPERLINK=1", "str"),
        ([("FORCE_HYPERLINK", "1")], "list"),
        (NotAMapping(), "NotAMapping"),
    ],
)
def test_detection_rejects_an_env_that_is_not_a_mapping(env: object, kind: str) -> None:
    with pytest.raises(TypeError, match=rf"^env must be a mapping, not {kind}$"):
        supports_hyperlinks(io.StringIO(), env=env, platform="linux")  # type: ignore[arg-type]


def test_an_env_type_name_is_cut_in_the_message() -> None:
    long_name: Any = type("N" * 60, (), {})()
    with pytest.raises(TypeError, match=r"^env must be a mapping, not N{40}$"):
        supports_hyperlinks(io.StringIO(), env=long_name, platform="linux")


@pytest.mark.parametrize("wrap", [dict, types.MappingProxyType, collections.ChainMap])
def test_detection_accepts_any_mapping_as_env(wrap: Callable[[dict[str, str]], object]) -> None:
    env: Any = wrap({"FORCE_HYPERLINK": "1"})
    assert supports_hyperlinks(io.StringIO(), env=env, platform="linux") is True


def test_detection_accepts_os_environ_as_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_HYPERLINK", "1")
    assert supports_hyperlinks(io.StringIO(), env=os.environ, platform="linux") is True
