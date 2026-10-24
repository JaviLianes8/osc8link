"""Seeded property tests: an independent character-by-character reader, round trips and
the stream filter, over random text built from the bytes that matter to the parser.

The reference reader below is written by hand from the rules in the README (the VTE
state machine, see test_vte_parser.py); it walks one character at a time and shares no
code or regular expression with the library.
"""

from __future__ import annotations

import random

import pytest

from osc8link import Link, contains_link, encode_url, iter_links, link, strip
from osc8link._cli import _strip_stream

ABORT = {"\x07", "\x18", "\x1a", "\x1b", *map(chr, range(0x80, 0xA0))}
BETWEEN = {*map(chr, range(0x18)), "\x19", *map(chr, range(0x1C, 0x20)), "\x7f"}
IGNORED = BETWEEN - {"\x07"}
STRINGS = {0x9B: "csi", 0x9D: "osc", 0x90: "string", 0x98: "string", 0x9E: "string"}
STRINGS[0x9F] = "string"
ALPHABET = ["\x1b", "]", "\x9d", "8", "0", ";", ":", "=", "i", "d", "\\", "\x07", "\x9c"]
ALPHABET += ["\x00", "\x18", "\x1a", "\x7f", "\x85", "a", "b", "\n", " ", chr(0x100)]
# Whole pieces make complete sequences common enough to matter.
ALPHABET += ["\x1b]8;", "\x9d8;", "\x1b]8;;", "id=a:", "http://x", "\x1b\\", "\x1b]8;;\x1b\\"]


def _sequence_at(s: str, i: int) -> tuple[int, str, str, bool] | None:
    """Read an OSC 8 sequence starting at i: (end, kept controls, payload, terminated)."""
    j, kept = i + 1, ""
    if s[i] == "\x1b":
        while j < len(s) and s[j] in BETWEEN:
            kept += s[j]
            j += 1
        if j == len(s) or s[j] != "]":
            return None
        j += 1
    elif s[i] != "\x9d":
        return None
    while j < len(s) and (s[j] == "0" or s[j] in IGNORED):
        j += 1
    if j == len(s) or s[j] != "8":
        return None
    k = j + 1
    while k < len(s) and s[k] in IGNORED:
        k += 1
    if k < len(s) and s[k] != ";" and s[k] not in ABORT:
        return None
    start = end = j + 1
    while end < len(s) and s[end] not in ABORT:
        end += 1
    payload = s[start:end]
    if s[end : end + 2] == "\x1b\\":
        return end + 2, kept, payload, True
    if end < len(s) and s[end] in "\x07\x9c":
        return end + 1, kept, payload, True
    return end, kept, payload, False


def _after(state: str, char: str) -> str:
    """The parser state after char: ground, esc, esc-int, csi, osc or string."""
    code = ord(char)
    if char in "\x18\x1a":
        return "ground"
    if char == "\x1b":
        return "esc"
    if 0x80 <= code <= 0x9F:
        return STRINGS.get(code, "ground")
    if state in ("ground", "osc", "string"):
        return "ground" if state == "osc" and char == "\x07" else state
    if code < 0x20 or code == 0x7F:
        return state
    if state == "esc":
        named = {"[": "csi", "]": "osc", "P": "string", "X": "string", "^": "string"}
        named["_"] = "string"
        return named.get(char, "esc-int" if 0x20 <= code <= 0x2F else "ground")
    if state == "esc-int":
        return state if 0x20 <= code <= 0x2F else "ground"
    return state if 0x20 <= code <= 0x3F else "ground"


def reference(s: str) -> tuple[str, list[Link], bool]:
    visible, links, pieces = "", [], ""
    opened = False
    current: tuple[str, str | None, tuple[tuple[str, str], ...]] | None = None
    state = "ground"
    i = 0
    while i < len(s):
        found = _sequence_at(s, i)
        if found is None:
            visible += s[i]
            pieces += s[i]
            state = _after(state, s[i])
            i += 1
            continue
        i, kept, payload, terminated = found
        # strip cancels a sequence the removed opener had ended, see test_strip_safety.py.
        visible += ("\x18" if state != "ground" else "") + kept.replace("\x7f", "")
        state = "ground"
        clean = "".join(char for char in payload if char >= " " and char != "\x7f")
        if not terminated or ";" not in clean[1:]:
            continue
        raw, uri = clean[1:].split(";", 1)
        if current is not None and pieces:
            links.append(Link(current[0], pieces, current[1], current[2]))
        pieces = ""
        params = tuple((k, v) for k, eq, v in (p.partition("=") for p in raw.split(":")) if eq)
        ident = next((v for k, v in params if k == "id"), "") or None
        current = (uri, ident, params) if uri else None
        opened = opened or bool(uri)
    if current is not None and pieces:
        links.append(Link(current[0], pieces, current[1], current[2]))
    return visible, links, opened


def _text(rng: random.Random, size: int) -> str:
    return "".join(rng.choice(ALPHABET) for _ in range(size))


@pytest.mark.parametrize("seed", range(6))
def test_the_library_reads_like_the_reference(seed: int) -> None:
    rng = random.Random(seed)
    found = 0
    for _ in range(4000):
        s = _text(rng, rng.randrange(0, 40))
        visible, links, opened = reference(s)
        assert strip(s) == visible, s
        assert list(iter_links(s)) == links, s
        assert contains_link(s) is opened, s
        found += len(links)
    assert found > 150


@pytest.mark.parametrize("seed", range(3))
def test_found_urls_hold_no_control_character(seed: int) -> None:
    rng = random.Random(100 + seed)
    for _ in range(3000):
        for found in iter_links(_text(rng, 60)):
            assert found.url
            assert not any(char < " " or "\x7f" <= char <= "\x9f" for char in found.url)


def _safe_text(rng: random.Random) -> str:
    pool = [*ALPHABET, "\x1b[31m", "e", chr(0x1F600)]
    while True:
        text = "".join(rng.choice(pool) for _ in range(rng.randrange(1, 12)))
        try:
            return link("u", text) and text
        except ValueError:
            continue


@pytest.mark.parametrize("seed", range(3))
def test_built_links_read_back_exactly(seed: int) -> None:
    rng = random.Random(200 + seed)
    for _ in range(2000):
        url = "".join(chr(rng.randrange(0x20, 0x3000)) for _ in range(rng.randrange(1, 10)))
        url = "".join(char for char in url if not 0xD800 <= ord(char) <= 0xDFFF) or "x"
        text = _safe_text(rng)
        ident = rng.choice([None, "", "a", "x-1", "!~"])
        end = rng.choice(["st", "bel"])
        built = link(url, text, id=ident, terminator=end)  # type: ignore[arg-type]
        params = (("id", ident),) if ident else ()
        assert list(iter_links("a" + built + "b")) == [
            Link(encode_url(url), text, ident or None, params)
        ]
        # Text that ends inside an escape sequence gets the CAN that the closing ESC stood for.
        assert strip(built) == reference(built)[0]
        assert strip(built) in (text, text + "\x18")


@pytest.mark.parametrize("seed", range(3))
def test_the_stream_filter_strips_like_strip_over_any_line_split(seed: int) -> None:
    rng = random.Random(300 + seed)
    for _ in range(2000):
        s = _text(rng, rng.randrange(0, 80))
        lines = s.splitlines(keepends=True)
        assert "".join(_strip_stream(lines)) == strip(s), s
