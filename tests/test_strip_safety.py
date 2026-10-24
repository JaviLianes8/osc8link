"""strip never builds a sequence out of the text on both sides of one it removes.

Written by hand. A terminal reads ESC, CAN, SUB and the C1 controls the same way in every
state, so the opener of an OSC 8 sequence also ends whatever escape sequence or control
string came before it. Once the sequence is gone, that earlier one would run on into the
text after it; strip leaves a CAN there instead, which ends it and shows nothing.
"""

from __future__ import annotations

import random

import pytest

from osc8link import contains_link, iter_links, strip

ST = "\x1b\\"


def test_a_dangling_escape_cannot_join_the_text_after_a_removed_sequence() -> None:
    text = "\x1b" + "\x1b]8;;\x07" + "]8;;https://evil.test\x07CLICK"
    assert not contains_link(text)
    stripped = strip(text)
    assert stripped == "\x1b\x18]8;;https://evil.test\x07CLICK"
    assert not contains_link(stripped)
    assert list(iter_links(stripped)) == []
    assert strip(stripped) == stripped


def test_a_dangling_escape_cannot_open_a_control_string() -> None:
    assert strip(f"\x1b\x1b]8;;\x07P1;2|data{ST}shown") == f"\x1b\x18P1;2|data{ST}shown"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"\x1b[1\x1b]8;;http://x.test{ST}Text\x1b]8;;{ST}", "\x1b[1\x18Text"),
        ("x\x1b\x1b]8;;http://x.test\x07Yes\x1b]8;;\x07", "x\x1b\x18Yes"),
        (f"\x1bP1\x1b]8;;http://x.test{ST}Text\x1b]8;;{ST}", "\x1bP1\x18Text"),
        (f"%\x18\U000a8318m\x9d\x9d\x1b]8;;{ST}08", "%\x18\U000a8318m\x9d\x9d\x1808"),
        ("\x9b1\x9d8;;http://x\x9cT", "\x9b1\x18T"),
        ("\x1b]0;title\x1b]8;;http://x\x07T", "\x1b]0;title\x18T"),
        ("\x1b \x1b]8;;http://x\x07T", "\x1b \x18T"),
        ("\x1b\x07\x1b\x05]8;;http://x\x07T", "\x1b\x07\x18\x05T"),
    ],
)
def test_an_unfinished_sequence_before_a_removed_one_is_cancelled(text: str, expected: str) -> None:
    assert strip(text) == expected
    assert strip(expected) == expected


@pytest.mark.parametrize(
    "before",
    ["", "a", "\x1b[31m", "\x1b[1mX", "\x1b]0;t\x07", f"\x1b]0;t{ST}", "\x1b7", "\x1b(B", "\x18"],
)
def test_finished_text_before_a_removed_sequence_gets_nothing_added(before: str) -> None:
    assert strip(f"{before}\x1b]8;;http://x{ST}T\x1b]8;;{ST}") == before + "T"


def test_a_cancel_is_added_only_once_for_adjacent_sequences() -> None:
    text = f"\x1b[1\x1b]8;;http://a{ST}\x1b]8;;{ST}\x1b]8;;http://b{ST}T"
    assert strip(text) == "\x1b[1\x18T"


ALPHABET = ["\x1b", "]", "\x9d", "8", "0", ";", "\\", "\x07", "\x9c", "[", "P", "1", "\n"]
ALPHABET += ["\x00", "\x18", "\x1a", "\x7f", "\x9b", "\x90", "a", " ", "m"]
ALPHABET += ["\x1b]8;", "\x1b]8;;", "http://x", ST, "\x1b]8;;\x1b\\", "\x1b]8;;http://x\x07"]


@pytest.mark.parametrize("seed", range(4))
def test_stripping_is_stable_and_never_draws_a_link(seed: int) -> None:
    rng = random.Random(500 + seed)
    for _ in range(20_000):
        text = "".join(rng.choice(ALPHABET) for _ in range(rng.randrange(0, 24)))
        stripped = strip(text)
        assert strip(stripped) == stripped, text
        assert not contains_link(stripped), text
        assert list(iter_links(stripped)) == [], text
