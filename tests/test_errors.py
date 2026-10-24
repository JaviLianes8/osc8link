"""Errors are typed, name the argument and never quote much of the caller's input."""

from __future__ import annotations

import io
from typing import Any

import pytest

from osc8link import (
    LinkError,
    auto_link,
    contains_link,
    encode_url,
    iter_links,
    link,
    strip,
    supports_hyperlinks,
)

HUGE = "x" * 1_000_000
LIMIT = 200


def _message(call: Any, *args: Any, **kwargs: Any) -> tuple[type[BaseException], str]:
    with pytest.raises((LinkError, TypeError)) as caught:
        call(*args, **kwargs)
    return caught.type, str(caught.value)


@pytest.mark.parametrize(
    ("kwargs", "words"),
    [
        ({"url": "", "text": "A"}, "url must not be empty"),
        ({"url": "https://a.test/\udc80", "text": "A"}, "lone surrogate"),
        ({"url": "https://a.test", "text": "A", "id": "a:b"}, "id must hold"),
        ({"url": "https://a.test", "text": "\x1b]8;;x\x1b\\" + HUGE}, "control string"),
        ({"url": "https://a.test", "text": "A", "terminator": "esc"}, "terminator must be"),
        ({"url": "https://a.test", "text": "A", "terminator": HUGE}, "1000000 characters"),
        ({"url": "https://a.test", "text": "A", "id": ";" + HUGE}, "id must hold"),
    ],
)
def test_bad_values_raise_link_error_with_a_short_message(
    kwargs: dict[str, Any], words: str
) -> None:
    for call in (link, auto_link):
        kind, message = _message(call, **kwargs)
        assert kind is LinkError
        assert words in message
        assert len(message) < LIMIT
        assert HUGE[:100] not in message


def test_link_error_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="url must not be empty"):
        link("", "A")


@pytest.mark.parametrize(
    ("kwargs", "name"),
    [
        ({"url": b"https://a.test", "text": "A"}, "url"),
        ({"url": "https://a.test", "text": None}, "text"),
        ({"url": "https://a.test", "text": "A", "id": 1}, "id"),
        ({"url": "https://a.test", "text": "A", "id": b""}, "id"),
        ({"url": "https://a.test", "text": "A", "terminator": 5}, "terminator"),
        ({"url": "https://a.test", "text": "A", "terminator": ["st"]}, "terminator"),
    ],
)
def test_wrong_types_raise_type_error_naming_the_argument(
    kwargs: dict[str, Any], name: str
) -> None:
    for call in (link, auto_link):
        kind, message = _message(call, **kwargs)
        assert kind is TypeError
        assert message.startswith(f"{name} must be a str, not ")


def test_a_fallback_that_is_not_a_str_is_a_type_error() -> None:
    with pytest.raises(TypeError, match=r"^fallback must be a str, not int$"):
        auto_link("https://a.test", "A", stream=io.StringIO(), fallback=1)  # type: ignore[arg-type]


@pytest.mark.parametrize("call", [strip, contains_link, iter_links, encode_url])
@pytest.mark.parametrize("bad", [b"bytes", None, 1, ["x"]])
def test_the_readers_reject_non_strings_at_once(call: Any, bad: object) -> None:
    # iter_links raises on the call itself, before the first item is asked for.
    with pytest.raises(TypeError, match=r"^(s|url) must be a str, not \w+$"):
        call(bad)


def test_a_type_name_in_a_message_is_cut_short() -> None:
    odd = type("T" * 10_000, (), {})()
    with pytest.raises(TypeError) as caught:
        strip(odd)
    assert len(str(caught.value)) < LIMIT


def test_detection_never_raises_on_odd_environment_values() -> None:
    odd = (chr(0x665), chr(0xFEFF) + "7", chr(0xA0) + "0")
    for value in ("", "\x00", HUGE, "9" * 5000, "-", "+", " ", *odd):
        for key in ("FORCE_HYPERLINK", "FORCE_COLOR", "TERM_PROGRAM_VERSION", "VTE_VERSION"):
            env = {key: value, "TERM_PROGRAM": "iTerm.app"}
            assert isinstance(supports_hyperlinks(io.StringIO(), env=env), bool)


@pytest.mark.parametrize("value", [1, b"1", None, 0.5, ["1"]])
@pytest.mark.parametrize("key", ["FORCE_HYPERLINK", "FORCE_COLOR", "TERM", "VTE_VERSION", "CI"])
def test_detection_treats_a_non_string_environment_value_as_unset(key: str, value: object) -> None:
    env: Any = {key: value, "TERM_PROGRAM": "ghostty"}
    assert supports_hyperlinks(io.StringIO(), env=env, platform="linux") is False
    assert supports_hyperlinks(_Tty(), env=env, platform="linux") is True


@pytest.mark.parametrize("platform", [1, b"linux", ["linux"]])
def test_detection_rejects_a_platform_that_is_not_a_str(platform: object) -> None:
    with pytest.raises(TypeError, match=r"^platform must be a str, not \w+$"):
        supports_hyperlinks(io.StringIO(), env={}, platform=platform)  # type: ignore[arg-type]


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


class _Raises:
    def isatty(self) -> bool:
        raise RuntimeError("boom")


class _NotCallable:
    isatty = None


@pytest.mark.parametrize("stream", [_Raises(), _NotCallable()])
def test_detection_says_no_whatever_a_broken_isatty_raises(stream: Any) -> None:
    assert supports_hyperlinks(stream, env={"TERM": "alacritty"}, platform="linux") is False
