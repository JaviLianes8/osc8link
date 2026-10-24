from __future__ import annotations

import enum
import io
import random
from typing import Any

import pytest

from osc8link import Link, auto_link, encode_url, iter_links, link, strip

ESC = "\x1b"
ST = "\x1b\\"
BEL = "\x07"


def _percent(char: str) -> str:
    return "".join(f"%{byte:02X}" for byte in char.encode("utf-8"))


def test_link_builds_an_osc8_sequence() -> None:
    built = link("https://example.com", "Example")
    assert built == f"{ESC}]8;;https://example.com{ST}Example{ESC}]8;;{ST}"


def test_link_includes_an_id_parameter_when_given() -> None:
    built = link("https://example.com", "Example", id="ref-1")
    assert built == f"{ESC}]8;id=ref-1;https://example.com{ST}Example{ESC}]8;;{ST}"


def test_an_empty_id_is_the_same_as_none() -> None:
    assert link("https://a.test", "A", id="") == link("https://a.test", "A")


def test_bel_terminator_ends_both_sequences_with_bel() -> None:
    built = link("https://a.test", "A", terminator="bel")
    assert built == f"{ESC}]8;;https://a.test{BEL}A{ESC}]8;;{BEL}"


def test_an_unknown_terminator_is_rejected() -> None:
    with pytest.raises(ValueError, match="terminator"):
        link("https://a.test", "A", terminator="esc")  # type: ignore[arg-type]


def test_non_ascii_url_characters_are_percent_encoded_as_utf8() -> None:
    built = link("https://en.wikipedia.org/wiki/Á", "A")
    assert "https://en.wikipedia.org/wiki/%C3%81" in built


def test_existing_percent_escapes_are_kept() -> None:
    assert encode_url("file:///tmp/%25gconf-tree.xml") == "file:///tmp/%25gconf-tree.xml"


def test_spaces_are_encoded() -> None:
    assert encode_url("https://a.test/a b") == "https://a.test/a%20b"


def test_every_printable_ascii_character_except_space_is_kept() -> None:
    printable = "".join(chr(code) for code in range(0x21, 0x7F))
    assert encode_url(printable) == printable


@pytest.mark.parametrize("control", ["\x1b", "\x07", "\n", "\r", "\x00", "\x7f", "\x9c", "\x9d"])
def test_control_characters_in_the_url_cannot_end_the_sequence(control: str) -> None:
    built = link(f"https://a.test/{control}x", "A")
    assert built.count(ESC) == 4
    assert BEL not in built
    assert list(iter_links(built)) == [Link(f"https://a.test/{_percent(control)}x", "A")]


def test_an_injected_sequence_in_the_url_stays_inside_the_target() -> None:
    evil = f"https://a.test/{ESC}]8;;https://evil.test{ST}"
    (found,) = iter_links(link(evil, "A") + " tail")
    assert found.text == "A"
    assert found.url.startswith("https://a.test/%1B]8;;https://evil.test%1B")


def test_payload_bytes_stay_in_the_printable_range_for_any_url() -> None:
    rng = random.Random(8)
    for _ in range(300):
        url = "".join(
            chr(rng.choice([rng.randrange(0x110000), rng.randrange(0x80)])) for _ in range(12)
        )
        url = "".join(char for char in url if not 0xD800 <= ord(char) <= 0xDFFF) or "x"
        target = encode_url(url)
        assert target and all(0x21 <= ord(char) <= 0x7E for char in target), url


def test_a_lone_surrogate_in_the_url_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="surrogate"):
        encode_url("https://a.test/\ud800")


def test_an_empty_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        link("", "A")


@pytest.mark.parametrize("bad", ["a:b", "a;b", "café", "a\x1bb", "a\nb", "\x7f"])
def test_an_id_outside_the_spec_alphabet_is_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="id"):
        link("https://a.test", "A", id=bad)


def test_an_id_may_use_every_other_printable_character() -> None:
    allowed = "".join(chr(c) for c in range(0x20, 0x7F) if chr(c) not in ":;")
    (found,) = iter_links(link("https://a.test", "A", id=allowed))
    assert found.id == allowed


@pytest.mark.parametrize(
    "opener",
    [f"{ESC}]", f"{ESC}P", f"{ESC}X", f"{ESC}^", f"{ESC}_", "\x90", "\x98", "\x9d", "\x9e", "\x9f"],
)
def test_text_holding_a_control_string_is_rejected(opener: str) -> None:
    with pytest.raises(ValueError, match="control string"):
        link("https://a.test", f"before {opener}8;;https://evil.test{ST}after")


def test_text_may_hold_colours_and_line_breaks() -> None:
    text = f"{ESC}[1;31mred{ESC}[m\nnext"
    (found,) = iter_links(link("https://a.test", text))
    assert found.text == text


@pytest.mark.parametrize("args", [(b"https://a.test", "A"), ("https://a.test", 5)])
def test_non_string_arguments_are_type_errors(args: tuple[object, object]) -> None:
    with pytest.raises(TypeError, match=r"^(url|text) must be a str, not (bytes|int)$"):
        link(*args)  # type: ignore[arg-type]


def test_a_non_string_id_is_a_type_error() -> None:
    with pytest.raises(TypeError, match=r"^id must be a str, not int$"):
        link("https://a.test", "A", id=7)  # type: ignore[arg-type]


def test_built_links_strip_back_to_their_text() -> None:
    assert strip("before " + link("https://a.test", "A", id="x") + " after") == "before A after"


class _Lies(str):
    """A str whose __str__, __format__ and __iter__ disagree with its characters."""

    def __str__(self) -> str:
        return "\x1b]8;;https://evil.test\x1b\x5c"

    def __format__(self, spec: str) -> str:
        return str(self)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter("")


class _Colour(str, enum.Enum):
    RED = "red"


@pytest.mark.parametrize("field", ["url", "text", "id", "terminator", "fallback"])
def test_a_str_subclass_is_written_as_its_characters(field: str) -> None:
    plain: dict[str, Any] = {"url": "https://ok.test", "text": "safe", "id": "a"}
    plain["terminator"] = "st"
    tricky = dict(plain)
    if field != "fallback":
        tricky[field] = _Lies(plain[field])
    pipe = io.StringIO()
    fallback = _Lies("{text} ({url})") if field == "fallback" else "{text} ({url})"
    assert link(**tricky) == link(**plain)
    assert auto_link(**tricky, stream=pipe, fallback=fallback) == auto_link(**plain, stream=pipe)


def test_an_id_that_hides_its_characters_from_iteration_is_still_checked() -> None:
    with pytest.raises(ValueError, match="id must hold"):
        link("https://ok.test", "t", id=_Lies("a;b\x1b]8;;https://evil.test\x1b\x5c"))


def test_a_str_enum_member_is_written_as_its_value() -> None:
    assert link("https://ok.test", _Colour.RED) == link("https://ok.test", "red")
    assert (
        auto_link("https://ok.test", _Colour.RED, stream=io.StringIO()) == "red (https://ok.test)"
    )
    assert strip(_Colour.RED) == "red" and type(strip(_Colour.RED)) is str
