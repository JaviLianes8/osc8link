"""The reading rules come from VTE's own state machine, read out of its source.

VTE is the terminal the OSC 8 spec was written for. Its parser (src/parser.hh) and OSC 8
handler (src/vteseq.cc) are pinned in tests/upstream/MANIFEST.json and not committed; these
tests skip until `python scripts/fetch_upstream.py` has fetched them. For every character
up to U+00A0 the case labels of VTE's `feed` and `OSC_STRING` switches say whether it is
ignored, collected, ends the sequence or aborts it, and `iter_links` must read it the same.
"""

from __future__ import annotations

import re

import pytest
from conftest import read_upstream

from osc8link import Link, contains_link, iter_links

CASE = re.compile(r"case (0x[0-9a-f]+)(?: \.\.\. (0x[0-9a-f]+))?:")


def _block(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _cases(block: str) -> dict[int, str]:
    """Map each code point named by a case label to the return statement it reaches."""
    actions: dict[int, str] = {}
    pending: list[int] = []
    for line in block.splitlines():
        for low, high in CASE.findall(line):
            pending.extend(range(int(low, 16), int(high or low, 16) + 1))
        if "return" in line and pending:
            for code in pending:
                actions.setdefault(code, line.strip())
            pending = []
    return actions


@pytest.fixture(scope="module")
def vte() -> str:
    return read_upstream("vte-parser.hh")


def _classify(vte: str, code: int) -> str:
    anywhere = _cases(_block(vte, "inline int feed(uint32_t raw)", "default: [[likely]]"))
    if code in anywhere:
        action = anywhere[code]
        if "OSC_STRING" in action:
            return "restart"
        return "ignore" if "action_nop" in action else "abort"
    osc = _cases(_block(vte, "case OSC_STRING:", "case ST_IGNORE:"))
    action = osc.get(code, "return action_osc_collect(raw);")
    if "action_nop" in action:
        return "ignore"
    if "ST_ESC" in action:
        return "abort"  # unless a backslash follows, see the ST test below
    return "dispatch" if "action_osc_dispatch" in action else "collect"


def test_the_source_has_the_expected_shape(vte: str) -> None:
    classes = [_classify(vte, code) for code in range(0xA1)]
    assert classes.count("dispatch") == 2  # BEL and the C1 ST
    assert classes.count("restart") == 1  # the C1 OSC
    assert "case 0x5d:                /* ']' */" in vte


@pytest.mark.parametrize("code", [*range(0xA1), 0x3000, 0x1F600])
def test_each_character_inside_a_payload_is_read_like_vte(vte: str, code: int) -> None:
    char = chr(code)
    kind = _classify(vte, code)
    # VTE dispatches only when opener and terminator are both C0 or both C1.
    opener = "\x9d" if code == 0x9C else "\x1b]"
    text = f"{opener}8;;http://a{char}b\x1b\\X"
    if kind == "ignore":
        assert list(iter_links(text)) == [Link("http://ab", "X")]
    elif kind == "collect":
        assert list(iter_links(text)) == [Link(f"http://a{char}b", "X")]
    elif kind == "dispatch":
        assert [found.url for found in iter_links(text)] == ["http://a"]
    else:
        assert list(iter_links(text)) == [] and not contains_link(text)
        restarted = f"\x1b]8;;http://a{char}8;;http://z\x9cX"
        expected = [Link("http://z", "X")] if kind == "restart" else []
        assert list(iter_links(restarted)) == expected


def test_esc_backslash_ends_the_sequence_and_esc_other_aborts(vte: str) -> None:
    st_esc = _block(vte, "case ST_ESC:", "case ESC:")
    assert "if (raw == 0x5c /* '\\' */)" in st_esc
    assert "return VTE_TRANSITION(raw, GROUND, action_osc_dispatch);" in st_esc
    assert list(iter_links("\x1b]8;;http://a\x1b\\X")) == [Link("http://a", "X")]
    assert list(iter_links("\x1b]8;;http://a\x1bxX")) == []


@pytest.mark.parametrize("code", [*range(0x20), 0x7F])
def test_controls_between_esc_and_the_bracket_follow_vte(vte: str, code: int) -> None:
    anywhere = _cases(_block(vte, "inline int feed(uint32_t raw)", "default: [[likely]]"))
    esc = _cases(_block(vte, "                case ESC:\n", "case ESC_INT:"))
    if code in anywhere:
        keeps = "action_nop" in anywhere[code]
    else:
        keeps = "action_execute" in esc[code] or "VTE_TRANSITION(raw, ESC," in esc[code]
    text = f"\x1b{chr(code)}]8;;http://a\x1b\\X"
    assert contains_link(text) is keeps


def test_mixed_c0_and_c1_controls_are_accepted_where_vte_drops_them(vte: str) -> None:
    # A documented difference: VTE checks ((introducer ^ terminator) & 0x80) == 0 and drops
    # the sequence otherwise; xterm.js and this library read it.
    assert "return ((introducer ^ terminator) & 0x80) == 0;" in vte
    assert [found.url for found in iter_links("\x9d8;;http://a\x07X")] == ["http://a"]
    assert [found.url for found in iter_links("\x1b]8;;http://a\x9cX")] == ["http://a"]


def test_the_osc8_handler_closes_on_an_empty_uri_and_reads_the_first_id() -> None:
    handler = _block(read_upstream("vte-vteseq.cc"), "Terminal::set_current_hyperlink(", "\n}\n")
    assert "if (subtoken[0] != 'i' || subtoken[1] != 'd' || subtoken[2] != '=')" in handler
    assert "if (len > 0 && len <= VTE_HYPERLINK_URI_LENGTH_MAX) {" in handler
    text = "\x1b]8;foo=1:id=a:id=b;http://a\x1b\\A\x1b]8;id=x;\x1b\\B"
    assert list(iter_links(text)) == [
        Link("http://a", "A", "a", (("foo", "1"), ("id", "a"), ("id", "b")))
    ]
