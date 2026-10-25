from __future__ import annotations

import io

import pytest

from osc8link import auto_link, link


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def ghostty(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("FORCE_HYPERLINK", "FORCE_COLOR", "CI", "TEAMCITY_VERSION", "WT_SESSION", "TERM"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "ghostty")
    monkeypatch.setattr("sys.platform", "linux")


def test_a_terminal_that_shows_links_gets_the_link(ghostty: None) -> None:
    built = auto_link("https://a.test/\u00e9", "A", stream=Tty(), id="x", terminator="bel")
    assert built == link("https://a.test/\u00e9", "A", id="x", terminator="bel")


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_the_platform_is_taken_from_sys_platform(
    ghostty: None, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    # auto_link has no platform argument: a Windows console without WT_SESSION gets the
    # fallback text, never escape codes, for the same tty and environment.
    monkeypatch.setattr("sys.platform", platform)
    built = auto_link("https://a.test", "A", stream=Tty())
    assert built == ("A (https://a.test)" if platform == "win32" else link("https://a.test", "A"))


def test_a_pipe_gets_text_and_the_encoded_url(ghostty: None) -> None:
    assert (
        auto_link("https://a.test/\u00e9", "A", stream=io.StringIO()) == "A (https://a.test/%C3%A9)"
    )


def test_the_fallback_format_is_configurable(ghostty: None) -> None:
    built = auto_link("https://a.test", "A", stream=io.StringIO(), fallback="[{text}]({url})")
    assert built == "[A](https://a.test)"


@pytest.mark.parametrize("text", ["https://a.test/\u00e9", "https://a.test/%C3%A9"])
def test_text_that_is_the_url_is_not_repeated(ghostty: None, text: str) -> None:
    assert auto_link("https://a.test/\u00e9", text, stream=io.StringIO()) == text


def test_stream_defaults_to_stdout(ghostty: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdout", Tty())
    assert auto_link("https://a.test", "A") == link("https://a.test", "A")
    monkeypatch.setattr("sys.stdout", io.StringIO())
    assert auto_link("https://a.test", "A") == "A (https://a.test)"


@pytest.mark.parametrize("stream", [Tty(), io.StringIO()])
def test_bad_input_fails_whatever_the_terminal(ghostty: None, stream: io.StringIO) -> None:
    with pytest.raises(ValueError):
        auto_link("", "A", stream=stream)
    with pytest.raises(ValueError):
        auto_link("https://a.test", "\x1b]8;;https://evil.test\x1b\\", stream=stream)
    with pytest.raises(ValueError):
        auto_link("https://a.test", "A", stream=stream, id="a;b")


def test_the_fallback_only_replaces_its_two_placeholders(ghostty: None) -> None:
    built = auto_link(
        "https://a.test",
        "{url}",
        stream=io.StringIO(),
        fallback="{0} {x} {text.__class__} {text}={url}",
    )
    assert built == "{0} {x} {text.__class__} {url}=https://a.test"
