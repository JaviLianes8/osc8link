"""The line-by-line `strip` filter at its hold limit, and when held lines go out."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from osc8link import contains_link, strip
from osc8link._cli import _strip_stream

OPENER = "\x1b]8;;https://a.test/\n"


def _stream(lines: list[str]) -> str:
    return "".join(_strip_stream(iter(lines)))


EVIL = "8;;https://evil.test\x07CLICK\n"
LIMIT = 1 << 16


@pytest.mark.parametrize("size", [LIMIT - 3, LIMIT, 2 * LIMIT])
@pytest.mark.parametrize(
    ("prefix", "rest"),
    [
        ("\x1b\n", "]" + EVIL),
        ("\x1b\r\n", "]" + EVIL),
        ("\x1b]\n", EVIL),
        ("\x1b]\r\n", EVIL),
        ("\x9d\n", EVIL),
        ("\x1b\x05\n", "]" + EVIL),
    ],
)
def test_a_long_line_ending_in_an_opener_still_holds_it(size: int, prefix: str, rest: str) -> None:
    lines = ["x" * size + prefix, rest]
    out = _stream(lines)
    assert out == strip("".join(lines))
    assert not contains_link(out)


@pytest.mark.parametrize(("prefix", "rest"), [("\x1b\n", "]" + EVIL), ("\x9d\n", EVIL)])
def test_an_opener_held_up_to_the_limit_is_ended_with_a_cancel(prefix: str, rest: str) -> None:
    # The held text is the opener and line breaks: 65,535 characters are held whole.
    lines = [prefix, *["\n"] * (LIMIT - 3), rest]
    assert _stream(lines) == strip("".join(lines))
    # At 65,536 it is let go, and a CAN ends it so the next line cannot complete it.
    lines = [prefix, *["\n"] * (LIMIT - 2), rest]
    out = _stream(lines)
    assert out == prefix[0] + "\n" * (LIMIT - 1) + "\x18" + rest
    assert not contains_link(out)


def _exact(held: int) -> list[str]:
    """An open sequence held through the fast path whose held text is held characters."""
    body = ["x" * 99 + "\n"] * 655
    rest = held - len(OPENER) - 655 * 100
    return [OPENER, *body, "x" * (rest - 1) + "\n", "\x07T\n"]


def _exact_rescanned(held: int) -> list[str]:
    """The same through the rescan path: the second line changes what the tail is."""
    line = ";;https://a.test/" + "x" * (held - 4 - 18) + "\n"
    return ["\x1b]8\n", line, "\x07T\n"]


@pytest.mark.parametrize("build", [_exact, _exact_rescanned])
def test_the_hold_limit_is_exactly_65_536_characters(build: Callable[[int], list[str]]) -> None:
    under, at = build(LIMIT - 1), build(LIMIT)
    assert len("".join(under[:-1])) == LIMIT - 1
    assert len("".join(at[:-1])) == LIMIT
    assert _stream(under) == "T\n" == strip("".join(under))
    assert _stream(at) == "\x07T\n"


def _timeline(lines: list[str]) -> list[tuple[int, str]]:
    """Each chunk written, with the number of lines read before it was written."""
    read = 0

    def source() -> Iterator[str]:
        nonlocal read
        for line in lines:
            read += 1
            yield line

    return [(read, chunk) for chunk in _strip_stream(source()) if chunk]


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (
            [OPENER, "T\x07done\n", "next\n", "more\n"],
            [(2, "done\n"), (3, "next\n"), (4, "more\n")],
        ),
        (
            ["a\x1b]8\n", "x\n", "y\n", "z\n"],
            [(1, "a"), (2, "\x1b]8\nx\n"), (3, "y\n"), (4, "z\n")],
        ),
        (
            ["a\x9d\n", "\x07\n", "y\n", "z\n"],
            [(1, "a"), (2, "\x9d\n\x07\n"), (3, "y\n"), (4, "z\n")],
        ),
        (
            ["a\x1b\n", "\n", "x\n", "y\n"],
            [(1, "a"), (3, "\x1b\n\nx\n"), (4, "y\n")],
        ),
    ],
)
def test_a_held_line_goes_out_as_soon_as_its_sequence_ends_or_breaks(
    lines: list[str], expected: list[tuple[int, str]]
) -> None:
    assert _timeline(lines) == expected


@pytest.mark.parametrize(
    "escape", ["\x1b[1", "\x1b", "\x1bP", "\x9b1"], ids=["csi", "esc", "dcs", "c1-csi"]
)
def test_a_let_go_opener_cancels_the_escape_left_unfinished_before_it(escape: str) -> None:
    # The opener is held from where it starts, so "a" and the escape go out first and the
    # escape is still unfinished when the held text reaches the limit and is let go.
    lines = _exact(LIMIT)
    lines[0] = "a" + escape + lines[0]
    assert len("".join(lines[:-1])) - len("a" + escape) == LIMIT
    # The opener ended the escape; with the opener dropped a CAN must end it, or the BEL
    # after it would be read as part of the escape.
    assert _stream(lines) == "a" + escape + "\x18" + "\x07T\n"


LINK_LINE = "\x1b]8;;https://a.test\x07T\x1b]8;;\x07\n"


LET_GO_PREFIXES = {
    "long-line": ["\x1b]" + "0" * (LIMIT + 10) + "\n"],
    "esc": ["\x1b\n", *["\n"] * (LIMIT - 2)],
    "c1-osc": ["\x9d\n", *["\n"] * (LIMIT - 2)],
}


@pytest.mark.parametrize("name", list(LET_GO_PREFIXES))
def test_after_a_let_go_the_next_line_is_stripped_as_it_comes(name: str) -> None:
    held = LET_GO_PREFIXES[name]
    # The opener prefix goes out whole with exactly one CAN after it; the line after it
    # starts afresh, so it comes out as strip() gives it on its own.
    assert _stream([*held, LINK_LINE]) == "".join(held) + "\x18" + strip(LINK_LINE)
    assert strip(LINK_LINE) == "T\n"
