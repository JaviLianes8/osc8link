from __future__ import annotations

import pickle

import pytest

from osc8link import Link, contains_link, iter_links, link, strip

ESC = "\x1b"
ST = "\x1b\\"
BEL = "\x07"
C1_OSC = "\x9d"
C1_ST = "\x9c"


def osc8(params: str, uri: str, end: str = ST, opener: str = f"{ESC}]") -> str:
    return f"{opener}8;{params};{uri}{end}"


CLOSE = osc8("", "")


def test_strip_keeps_surrounding_plain_text() -> None:
    assert strip("before " + link("https://a.test", "A") + " after") == "before A after"


def test_plain_text_is_untouched() -> None:
    plain = f"no links here, 100% clean {ESC}[1mbold{ESC}[m"
    assert strip(plain) == plain
    assert contains_link(plain) is False
    assert list(iter_links(plain)) == []


@pytest.mark.parametrize("opener", [f"{ESC}]", C1_OSC])
@pytest.mark.parametrize("end", [ST, BEL, C1_ST])
def test_every_opener_and_terminator_is_read(opener: str, end: str) -> None:
    text = osc8("", "https://x.test", end, opener) + "X" + osc8("", "", end, opener)
    assert strip(text) == "X"
    assert contains_link(text) is True
    assert list(iter_links(text)) == [Link("https://x.test", "X")]


def test_strip_removes_mixed_terminators() -> None:
    assert strip(osc8("", "https://x.test", BEL) + "X" + osc8("", "", C1_ST)) == "X"


def test_strip_removes_malformed_osc8_sequences_too() -> None:
    assert strip(f"a{ESC}]8;nosemicolon{ST}b{ESC}]8{BEL}c") == "abc"


def test_strip_leaves_other_osc_commands_alone() -> None:
    title = f"{ESC}]0;title{BEL}{ESC}]80;x{ST}"
    assert strip(title) == title


def test_an_escape_inside_the_payload_aborts_the_sequence() -> None:
    broken = f"{ESC}]8;;https://a.test{ESC}[31mred{ESC}]8;;{ST}"
    assert strip(broken) == f"{ESC}[31mred"
    assert contains_link(broken) is False
    assert list(iter_links(broken)) == []


def test_an_unterminated_sequence_is_hidden_but_not_a_link() -> None:
    text = f"before {ESC}]8;;https://a.test and more"
    assert strip(text) == "before "
    assert contains_link(text) is False
    assert list(iter_links(text)) == []


def test_contains_link_ignores_a_close_alone() -> None:
    assert contains_link("x" + CLOSE) is False
    assert contains_link(osc8("id=1", "") + "x") is False


def test_the_uri_may_hold_semicolons() -> None:
    url = "https://a.test/path;param?q=1;2"
    assert list(iter_links(osc8("", url) + "A" + CLOSE)) == [Link(url, "A")]


def test_iter_links_yields_links_in_order() -> None:
    text = link("https://a.test", "A") + "gap" + link("https://b.test", "B")
    assert list(iter_links(text)) == [Link("https://a.test", "A"), Link("https://b.test", "B")]


def test_a_link_unpacks_as_url_and_text() -> None:
    (only,) = iter_links(link("https://u.test", "visible", id="x"))
    url, visible = only
    assert (url, visible) == ("https://u.test", "visible")


def test_an_open_without_a_close_switches_the_target() -> None:
    text = osc8("", "https://a.test") + "A" + osc8("", "https://b.test") + "B" + CLOSE + "C"
    assert list(iter_links(text)) == [Link("https://a.test", "A"), Link("https://b.test", "B")]


def test_a_link_left_open_runs_to_the_end() -> None:
    text = "x " + osc8("", "https://a.test") + "to the end\n"
    assert list(iter_links(text)) == [Link("https://a.test", "to the end\n")]


def test_links_without_visible_text_are_skipped() -> None:
    text = (
        osc8("", "https://a.test") + CLOSE + osc8("", "https://b.test") + osc8("", "https://c.test")
    )
    assert list(iter_links(text)) == []


def test_a_malformed_sequence_inside_a_link_is_dropped_from_the_text() -> None:
    text = osc8("", "https://a.test") + f"A{ESC}]8;junk{ST}B" + CLOSE
    assert list(iter_links(text)) == [Link("https://a.test", "AB")]


def test_closing_twice_is_harmless() -> None:
    text = CLOSE + link("https://a.test", "A") + CLOSE + "tail"
    assert list(iter_links(text)) == [Link("https://a.test", "A")]


def test_params_and_id_are_read() -> None:
    (found,) = iter_links(osc8("foo=bar:id=1:baz=quux", "https://a.test") + "A" + CLOSE)
    assert found.id == "1"
    assert found.params == (("foo", "bar"), ("id", "1"), ("baz", "quux"))


def test_an_empty_id_reads_as_none() -> None:
    (found,) = iter_links(osc8("id=", "https://a.test") + "A" + CLOSE)
    assert found.id is None
    assert found.params == (("id", ""),)


def test_params_without_a_value_are_ignored() -> None:
    (found,) = iter_links(osc8("::flag:id=z::", "https://a.test") + "A" + CLOSE)
    assert found.params == (("id", "z"),)


def test_the_first_id_wins_and_the_key_is_lowercase() -> None:
    (found,) = iter_links(osc8("ID=up:id=a:id=b", "https://a.test") + "A" + CLOSE)
    assert found.id == "a"


def test_links_are_values() -> None:
    found = Link("https://a.test", "A", "x", (("id", "x"),))
    assert pickle.loads(pickle.dumps(found)) == found
    assert hash(found) == hash(Link("https://a.test", "A", "x", (("id", "x"),)))
    with pytest.raises(AttributeError):
        found.url = "other"  # type: ignore[misc]
