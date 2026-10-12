"""Regression tests: read text the way the DEC parser of xterm and VTE reads it.

Written by hand. In that parser a C0 control between ESC and the final byte is executed
and DEL is ignored, so neither breaks an opener; inside an OSC string the C0 controls are
ignored, while ESC, CAN, SUB and every C1 control abort it.
"""

from __future__ import annotations

import time

import pytest

from osc8link import Link, contains_link, iter_links, link, strip

ESC = "\x1b"
ST = "\x1b\\"
INTERMEDIATES = ["\x00", "\x05", "\x07", "\n", "\r", "\x17", "\x19", "\x1c", "\x1f", "\x7f"]


@pytest.mark.parametrize("between", INTERMEDIATES)
def test_text_cannot_hide_an_opener_behind_a_control(between: str) -> None:
    with pytest.raises(ValueError, match="control string"):
        link("https://a.test", f"{ESC}{between}]8;;https://evil.test{ST}click")


@pytest.mark.parametrize("final", ["P", "X", "^", "_"])
def test_other_control_strings_with_a_control_inside_are_refused(final: str) -> None:
    with pytest.raises(ValueError, match="control string"):
        link("https://a.test", f"{ESC}\x00{final}data")


@pytest.mark.parametrize("canceller", ["\x18", "\x1a", ESC])
def test_cancel_before_the_bracket_breaks_the_opener(canceller: str) -> None:
    text = f"{ESC}{canceller}]8;;https://a.test{ST}"
    # CAN and SUB cancel the escape; a second ESC starts a fresh one that does open.
    assert contains_link(text) is (canceller == ESC)


@pytest.mark.parametrize("between", INTERMEDIATES)
def test_an_opener_with_a_control_inside_is_read(between: str) -> None:
    text = f"{ESC}{between}]8;;https://a.test{ST}A{ESC}]8;;{ST}"
    assert list(iter_links(text)) == [Link("https://a.test", "A")]
    # The executed control stays on screen; DEL is ignored.
    assert strip(text) == between.replace("\x7f", "") + "A"


def test_ignored_controls_inside_the_payload_drop_out_of_the_url() -> None:
    text = f"{ESC}]8;id=\x01x;https://a.\ntest/\x00p{ST}A{ESC}]8;;{ST}"
    assert list(iter_links(text)) == [Link("https://a.test/p", "A", "x", (("id", "x"),))]


def test_a_c1_opener_inside_a_payload_restarts_the_sequence() -> None:
    text = "\x9d8;;http://a\x9d8;;http://b\x9cB"
    assert list(iter_links(text)) == [Link("http://b", "B")]
    assert strip(text) == "B"


@pytest.mark.parametrize("abort", ["\x18", "\x1a", "\x80", "\x90", "\x98", "\x9e", "\x9f"])
def test_cancel_sub_and_c1_controls_abort_the_payload(abort: str) -> None:
    text = f"{ESC}]8;;http://a{abort}b{ST}B"
    assert contains_link(text) is False
    assert list(iter_links(text)) == []
    assert strip(text) == f"{abort}b{ST}B"


def test_a_leading_zero_in_the_command_number_is_still_osc8() -> None:
    text = f"{ESC}]08;;http://a{ST}X{ESC}]8;;{ST}"
    assert list(iter_links(text)) == [Link("http://a", "X")]
    assert strip(text) == "X"


def test_other_numbers_are_not_osc8() -> None:
    text = f"{ESC}]80;;x{ST}{ESC}]18;;x{ST}{ESC}]8x;;y{ST}"
    assert strip(text) == text


@pytest.mark.parametrize(
    "attack", ["\x9d8;", f"{ESC}]8;", f"{ESC}\x00]8;", f"{ESC}]8;;", "\x9d8;;x\x18", f"{ESC}\x00"]
)
def test_adversarial_input_is_read_in_linear_time(attack: str) -> None:
    text = attack * (1_000_000 // len(attack))
    started = time.perf_counter()
    strip(text)
    contains_link(text)
    list(iter_links(text))
    assert time.perf_counter() - started < 3
