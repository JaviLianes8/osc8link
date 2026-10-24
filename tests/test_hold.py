"""What the line-by-line `strip` filter holds back, for how long, and at what cost."""

from __future__ import annotations

import random
import time

import pytest

from osc8link import contains_link, strip
from osc8link._cli import _strip_stream
from osc8link._screen import strip_part
from osc8link._sequences import unfinished_tail

OPENER = "\x1b]8;;https://a.test/\n"


def _stream(lines: list[str]) -> str:
    return "".join(_strip_stream(iter(lines)))


@pytest.mark.parametrize(
    "lines",
    [
        ["a\x1b\x07\n", "]8;;https://evil.test\x07CLICK\n"],
        ["a\x1b\n", "]8;;https://evil.test\x07CLICK\n"],
        ["a\x1b\r\n", "]8;;https://evil.test\x07CLICK\n"],
        ["a\x1b\n", "\n", "\x05\n", "]8;;https://evil.test\x07CLICK\n"],
        ["a\x1b]\n", "8;;https://evil.test\x07CLICK\n"],
        ["a\x1b]0\n", "0\n", "8;;https://evil.test\x07CLICK\n"],
        ["a\x9d\n", "8;;https://evil.test\x9cCLICK\n"],
        ["a\x1b]8\n", "\n", ";;https://evil.test\x07CLICK\n"],
        ["a\x1b\n", "]8;;http://x.test\x07T\x1b]8;;\x07\n"],
    ],
)
def test_an_opener_split_over_lines_is_held_until_it_is_complete(lines: list[str]) -> None:
    out = _stream(lines)
    assert out == strip("".join(lines))
    assert not contains_link(out)
    assert "CLICK" in out or "T" in out


@pytest.mark.parametrize("tail", ["a\x1b\x01\n", "a\x1b]\n", "a\x1b]00\x02\n", "a\x9d\n"])
def test_an_opener_that_cannot_be_completed_any_more_is_let_go(tail: str) -> None:
    chunks = _strip_stream(iter([tail, "x\n", "y\n"]))
    assert next(chunks) == "a"
    assert next(chunks) == tail[1:] + "x\n"


def test_more_than_64_ki_characters_held_are_let_go() -> None:
    body = ["x" * 99 + "\n"] * 1000
    lines = [OPENER, *body, "\x07T\n"]
    # The held text reaches 65,536 characters with line 656; it is dropped as the terminal
    # would hide it, and what follows is no longer inside a sequence.
    assert len(OPENER) + 655 * 100 < 1 << 16 <= len(OPENER) + 656 * 100
    assert _stream(lines) == ("x" * 99 + "\n") * 344 + "\x07T\n"
    assert strip("".join(lines)) == "T\n"


def test_an_open_sequence_just_under_the_limit_is_held_whole() -> None:
    lines = [OPENER, *["x" * 99 + "\n"] * 655, "\x07T\n"]
    assert _stream(lines) == "T\n"


# An opener and the lines that keep it open: line breaks, payload text, or both mixed.
HELD = [(opener, ["\n"]) for opener in [OPENER, "\x1b\n", "\x1b]\n", "\x1b]8\n", "\x9d0\n"]]
HELD += [(OPENER, ["x\n"]), (OPENER, ["x\n", "\x05\n", "\n"]), ("\x9d8;\n", ["x\x7fy\n"])]


@pytest.mark.parametrize(("opener", "body"), HELD)
def test_holding_scans_each_character_a_bounded_number_of_times(
    monkeypatch: pytest.MonkeyPatch, opener: str, body: list[str]
) -> None:
    lines = ([opener] + body * (20_000 // len(body))) * 2
    scanned = 0

    def counted_tail(s: str) -> int:
        nonlocal scanned
        scanned += len(s)
        return unfinished_tail(s)

    def counted_part(s: str, state: str = "") -> tuple[str, str]:
        nonlocal scanned
        scanned += len(s)
        return strip_part(s, state)

    monkeypatch.setattr("osc8link._cli.unfinished_tail", counted_tail)
    monkeypatch.setattr("osc8link._cli.strip_part", counted_part)
    _stream(lines)
    assert scanned <= 4 * len("".join(lines))


@pytest.mark.parametrize("body", ["\n", "x\n"])
def test_a_hostile_open_sequence_streams_about_as_fast_as_plain_text(body: str) -> None:
    hostile = ([OPENER] + [body] * 30_000) * 2
    plain = ["line\n"] * (len(hostile) // 2)
    start = time.perf_counter()
    _stream(plain)
    plain_time = time.perf_counter() - start
    start = time.perf_counter()
    _stream(hostile)
    # Rescanning the held text for every line took about 6 s here; linear work, 0.1 s.
    assert time.perf_counter() - start < 10 * plain_time + 2.0


SPLIT = ["\x1b", "]", "\x9d", "8", "0", ";", "\n", "\r", "\x05", "\x07", "\x9c", "\\", "a"]
SPLIT += ["\x1b]8;;", "http://x", "\x1b\\", "\x18", "\x7f", "[", "1"]


@pytest.mark.parametrize("seed", range(3))
def test_the_stream_filter_equals_strip_whatever_the_line_breaks(seed: int) -> None:
    rng = random.Random(700 + seed)
    for _ in range(4000):
        text = "".join(rng.choice(SPLIT) for _ in range(rng.randrange(0, 40)))
        lines = text.split("\n")
        lines = [line + "\n" for line in lines[:-1]] + [lines[-1]]
        assert _stream(lines) == strip(text), text
