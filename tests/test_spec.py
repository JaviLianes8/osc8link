"""Check the library against the OSC 8 specification and ECMA-48.

The spec is "Hyperlinks (a.k.a. HTML-like anchors) in terminal emulators" by Egmont
Koblinger, fetched 2026-10-12 from gist revision 5965d6de1b609d8be0ff57b5ad9d4fe172500cf7:
https://gist.githubusercontent.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda/raw/5965d6de1b609d8be0ff57b5ad9d4fe172500cf7/Hyperlinks_in_Terminal_Emulators.md
It is committed unchanged as tests/data/egmontkob-hyperlinks.md and the examples below are
extracted from it at test time. The ECMA-48 checks are written by hand from clauses 8.3.89
(OSC) and 8.3.143 (ST) of the 5th edition, quoted in the comments.
"""

from __future__ import annotations

import hashlib
import random
import re

from osc8link import Link, encode_url, iter_links, link, strip

EN_DASH = chr(0x2013)
SPEC_SHA256 = "fc706ddcaeab44f2a117aa94bd3e9bc583132ba908281b5bb62ad3f58367955f"


def _printf(argument: str) -> str:
    """Expand the printf escapes the spec example uses: \\e, \\\\ and \\n."""
    escapes = {"e": "\x1b", "\\": "\\", "n": "\n"}
    return re.sub(r"\\(.)", lambda match: escapes[match.group(1)], argument)


def test_the_pinned_spec_is_the_fetched_revision(spec_text: str) -> None:
    digest = hashlib.sha256(spec_text.encode("utf-8", "surrogateescape")).hexdigest()
    assert digest == SPEC_SHA256


def test_the_spec_quick_example_is_built_byte_for_byte(spec_text: str) -> None:
    (argument,) = re.findall(r"^printf '(.*)'$", spec_text, flags=re.MULTILINE)
    expected = _printf(argument)
    assert link("http://example.com", "This is a link") + "\n" == expected
    assert list(iter_links(expected)) == [Link("http://example.com", "This is a link")]
    assert strip(expected) == "This is a link\n"


def test_the_spec_syntax_lines_match_the_built_shape(spec_text: str) -> None:
    assert "`OSC` `8` `;` `params` `;` `URI` `ST`" in spec_text
    assert "`OSC` `8` `;` `;` `ST`" in spec_text
    assert "`OSC` (operating system command) is typically `ESC` `]`." in spec_text
    assert "terminated with `ST` (string terminator) which is typically `ESC` `\\`" in spec_text
    built = link("https://a.test", "A", id="x")
    assert built.startswith("\x1b]8;id=x;https://a.test\x1b\\")
    assert built.endswith("\x1b]8;;\x1b\\")


def test_the_spec_params_example_is_read(spec_text: str) -> None:
    (params,) = re.findall(r"Example: `([^`]+)`\. Currently only the `id` key", spec_text)
    (found,) = iter_links(f"\x1b]8;{params};https://a.test\x1b\\A\x1b]8;;\x1b\\")
    assert found.id == "xyz123"
    assert found.params == (("id", "xyz123"), ("foo", "bar"), ("baz", "quux"))


def test_the_spec_c1_bytes_are_read(spec_text: str) -> None:
    osc, st = re.findall(r"`(0x9[cd])`", spec_text)[:2]
    assert (osc, st) == ("0x9d", "0x9c")
    sequence = f"{chr(int(osc, 16))}8;;https://a.test{chr(int(st, 16))}A"
    assert list(iter_links(sequence)) == [Link("https://a.test", "A")]


def test_the_spec_bel_alternative_is_read(spec_text: str) -> None:
    assert "often the `BEL` (`\\a`) character is used instead" in spec_text
    assert list(iter_links("\x1b]8;;https://a.test\aA\x1b]8;;\a")) == [Link("https://a.test", "A")]


def test_the_spec_byte_range_for_the_uri_holds(spec_text: str) -> None:
    assert "must not contain any bytes outside of the 32" + EN_DASH + "126 range" in spec_text
    assert "Bytes outside of this range in the URI must be URI-encoded." in spec_text
    rng = random.Random(48)
    for _ in range(200):
        url = "".join(chr(rng.randrange(0xD800)) for _ in range(8))
        assert all(32 <= ord(char) <= 126 for char in encode_url(url))


def test_the_spec_forbids_colon_and_semicolon_in_param_values(spec_text: str) -> None:
    assert "additional parameter values cannot contain the `:` and `;` characters" in spec_text


def test_built_payload_is_an_ecma48_command_string() -> None:
    # ECMA-48 8.3.89: "The command string following may consist of a sequence of bit
    # combinations in the range 00/08 to 00/13 and 02/00 to 07/14." 8.3.143: ST is
    # "09/12 or ESC 05/12". The payload is everything between ESC ] and ESC \.
    rng = random.Random(1991)
    allowed = {*range(0x08, 0x0E), *range(0x20, 0x7F)}
    for _ in range(200):
        url = "".join(chr(rng.randrange(0x30000)) for _ in range(10))
        url = "".join(char for char in url if not 0xD800 <= ord(char) <= 0xDFFF) or "u"
        built = link(url, "A", id="i-1")
        for payload in re.findall(r"\x1b\](.*?)\x1b\\", built):
            assert {ord(char) for char in payload} <= allowed, url
