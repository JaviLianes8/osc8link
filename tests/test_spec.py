"""Check the library against the OSC 8 specification and ECMA-48.

The spec is "Hyperlinks (a.k.a. HTML-like anchors) in terminal emulators" by Egmont
Koblinger, gist revision 5965d6de1b609d8be0ff57b5ad9d4fe172500cf7 (URL, size and sha256 in
tests/upstream/MANIFEST.json). The file is not committed: the tests that read it skip until
`python scripts/fetch_upstream.py` has fetched it. The ECMA-48 checks are written by hand
from clauses 8.3.89 (OSC) and 8.3.143 (ST) of the 5th edition.
"""

from __future__ import annotations

import random
import re

from osc8link import Link, encode_url, iter_links, link, strip

# The bytes printed by the spec's "Quick example" printf command, copied from
# https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda (section "Quick
# example") with its printf escapes expanded: \e is ESC, \\ is a backslash, \n a newline.
QUICK_EXAMPLE = "\x1b]8;;http://example.com\x1b\\This is a link\x1b]8;;\x1b\\\n"


def _printf(argument: str) -> str:
    """Expand the printf escapes the spec example uses: \\e, \\\\ and \\n."""
    escapes = {"e": "\x1b", "\\": "\\", "n": "\n"}
    return re.sub(r"\\(.)", lambda match: escapes[match.group(1)], argument)


def test_the_spec_quick_example_is_built_byte_for_byte() -> None:
    assert link("http://example.com", "This is a link") + "\n" == QUICK_EXAMPLE
    assert list(iter_links(QUICK_EXAMPLE)) == [Link("http://example.com", "This is a link")]
    assert strip(QUICK_EXAMPLE) == "This is a link\n"


def test_the_quick_example_matches_the_fetched_spec(spec_text: str) -> None:
    (argument,) = re.findall(r"^printf '(.*)'$", spec_text, flags=re.MULTILINE)
    assert _printf(argument) == QUICK_EXAMPLE


def test_the_built_shape_follows_the_spec_syntax() -> None:
    # Open: OSC 8 ; params ; URI ST. Close: OSC 8 ; ; ST. OSC is ESC ], ST is ESC backslash.
    built = link("https://a.test", "A", id="x")
    assert built == "\x1b]8;id=x;https://a.test\x1b\\A\x1b]8;;\x1b\\"


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


def test_the_spec_bel_alternative_is_read() -> None:
    assert list(iter_links("\x1b]8;;https://a.test\aA\x1b]8;;\a")) == [Link("https://a.test", "A")]


_RANGES = (range(0xD800), range(0xE000, 0x110000))


def test_the_uri_carries_only_bytes_32_to_126() -> None:
    # The spec allows only bytes 32 to 126 in the URI and asks for URI-encoding of the rest.
    rng = random.Random(48)
    for _ in range(200):
        url = "".join(chr(rng.choice(rng.choice(_RANGES))) for _ in range(8))
        assert all(32 <= ord(char) <= 126 for char in encode_url(url))


def test_built_payload_is_an_ecma48_command_string() -> None:
    # ECMA-48 8.3.89 limits an OSC command string to bit combinations 00/08 to 00/13 and
    # 02/00 to 07/14; 8.3.143 gives ST as 09/12 or ESC 05/12. The payload is everything
    # between ESC ] and ESC backslash.
    rng = random.Random(1991)
    allowed = {*range(0x08, 0x0E), *range(0x20, 0x7F)}
    for _ in range(200):
        url = "".join(chr(rng.randrange(0x30000)) for _ in range(10))
        url = "".join(char for char in url if not 0xD800 <= ord(char) <= 0xDFFF) or "u"
        built = link(url, "A", id="i-1")
        for payload in re.findall(r"\x1b\](.*?)\x1b\\", built):
            assert {ord(char) for char in payload} <= allowed, url
