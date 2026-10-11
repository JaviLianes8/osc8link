from __future__ import annotations

from osc8link import Link, contains_link, iter_links, link, strip

ESC = "\x1b"
ST = "\x1b\\"
BEL = "\x07"


def test_link_builds_an_osc8_sequence() -> None:
    built = link("https://example.com", "Example")
    assert built == f"{ESC}]8;;https://example.com{ST}Example{ESC}]8;;{ST}"


def test_link_includes_an_id_parameter_when_given() -> None:
    built = link("https://example.com", "Example", id="ref-1")
    assert built == f"{ESC}]8;id=ref-1;https://example.com{ST}Example{ESC}]8;;{ST}"


def test_strip_returns_the_visible_text_only() -> None:
    assert strip(link("https://example.com", "Example")) == "Example"


def test_strip_keeps_surrounding_plain_text() -> None:
    line = "before " + link("https://a.test", "A") + " after"
    assert strip(line) == "before A after"


def test_contains_link_is_true_for_a_hyperlink() -> None:
    assert contains_link(link("https://example.com", "Example")) is True


def test_contains_link_is_false_for_plain_text() -> None:
    assert contains_link("just some text with no escapes") is False


def test_iter_links_yields_url_and_text_pairs() -> None:
    text = link("https://a.test", "A") + "gap" + link("https://b.test", "B")
    assert list(iter_links(text)) == [
        Link("https://a.test", "A"),
        Link("https://b.test", "B"),
    ]


def test_iter_links_unpacks_as_url_text() -> None:
    (only,) = list(iter_links(link("https://u.test", "visible")))
    url, visible = only
    assert url == "https://u.test"
    assert visible == "visible"


def test_parse_accepts_a_bel_terminator() -> None:
    sequence = f"{ESC}]8;;https://bel.test{BEL}Clickable{ESC}]8;;{BEL}"
    assert contains_link(sequence) is True
    assert list(iter_links(sequence)) == [Link("https://bel.test", "Clickable")]
    assert strip(sequence) == "Clickable"


def test_plain_text_is_untouched_by_strip() -> None:
    plain = "no links here, 100% clean"
    assert strip(plain) == plain


def test_strip_removes_both_terminator_styles() -> None:
    mixed = f"{ESC}]8;;https://x.test{BEL}X{ESC}]8;;{ST}"
    assert strip(mixed) == "X"
