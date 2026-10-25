"""Read links the way a real terminal emulator does: xterm.js (@xterm/headless) as oracle.

Seeded random text mixing OSC 8 sequences, every opener and terminator, ignored and
aborting controls and cut-short sequences is written into a fresh @xterm/headless terminal
(version pinned in tests/upstream/MANIFEST.json). Every character the terminal prints must
carry the same link URI in `iter_links`. The visible characters come from a pool that never
appears inside a sequence, each used once per text, so they line up without ambiguity.

This library reads text the way VTE does (see test_vte_parser.py). Three shapes where
xterm.js differs from VTE are kept out of the generator and pinned below: an OSC 8 with
parameters but no URI (VTE closes the link, xterm.js keeps it open), DEL inside the URI
(VTE drops it, xterm.js keeps it) and ESC followed by anything but a backslash inside the
sequence (VTE drops the sequence, xterm.js applies it). A fourth is pinned the other way:
VTE's length limits (a URI over 2083 bytes, an id over 250 bytes, an OSC over 4096 code
points), which xterm.js and this library do not apply.
"""

from __future__ import annotations

import random

import pytest
from oracles import xterm_cells

from osc8link import iter_links, strip

POOL = [chr(code) for code in range(0x100, 0x180)]
A, B, C, D, E = POOL[:5]
OPENERS = ["\x1b]", "\x9d", "\x1b\x00]", "\x1b\x7f]", "\x1b\x05\x1f]"]
NUMBERS = ["8", "8", "8", "08", "80", "18"]
ENDS = ["\x1b\\", "\x07", "\x9c"]
IGNORED = ["\x00", "\x01", "\x06", "\x10", "\x17", "\x19", "\x1c", "\x1f"]
ABORTS = ["\x18", "\x1a", "\x80", "\x99", "\x9a"]
PARAMS = ["", "", "id=a", "id=b", "foo=bar:id=a", "id=", " "]
URIS = ["http://a.test/", "https://b.test/x;y", "file:///c", "mailto:d@e", "x", "~"]


def _payload(rng: random.Random) -> str:
    params = rng.choice(PARAMS)
    uri = rng.choice(URIS) if params.strip() or rng.random() < 0.7 else ""
    body = params + ";" + uri
    noisy = "".join(char + (rng.choice(IGNORED) if rng.random() < 0.1 else "") for char in body)
    return ";" + noisy if rng.random() < 0.97 else noisy


def _sequence(rng: random.Random) -> str:
    text = rng.choice(OPENERS) + rng.choice(NUMBERS) + _payload(rng)
    if rng.random() < 0.08:
        return text + rng.choice(ABORTS)
    return text + rng.choice(ENDS)


def _case(rng: random.Random) -> str:
    pool = POOL[:]
    rng.shuffle(pool)
    parts: list[str] = []
    for _ in range(rng.randrange(1, 12)):
        parts.append(_sequence(rng))
        parts.append("".join(pool.pop() for _ in range(rng.randrange(0, 4))))
    if rng.random() < 0.3:
        # A sequence cut short by the end of the text (xterm.js would apply one cut by ESC).
        last = _sequence(rng)
        parts.append(last[: rng.randrange(1, len(last))])
    return "".join(parts)


def _ours(text: str) -> dict[str, str | None]:
    """Map each pool character that strip keeps to the URI iter_links gives it."""
    owner: dict[str, str | None] = {char: None for char in strip(text) if char in POOL}
    for found in iter_links(text):
        for char in found.text:
            if char in POOL:
                owner[char] = found.url
    return owner


def _terminal(text: str) -> list[tuple[str, str | None]]:
    return [cell for cell in xterm_cells([text])[0] if cell[0] in POOL]


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_every_printed_character_carries_the_terminals_link(seed: int) -> None:
    rng = random.Random(seed)
    cases = [_case(rng) for _ in range(500)]
    compared = linked = 0
    for text, cells in zip(cases, xterm_cells(cases), strict=True):
        ours = _ours(text)
        for char, uri in cells:
            if char not in POOL:
                continue
            assert char in ours, (text, char)
            assert ours[char] == uri, (text, char, uri)
            compared += 1
            linked += uri is not None
    assert compared > 1000
    assert linked > 300


def test_the_hand_written_shapes_agree() -> None:
    cases = [
        f"\x1b]8;;http://a\x01b\x07{A}{B}",
        f"\x9d8;;http://c\x9c{A}\x9d8;;\x9c{B}",
        f"\x1b]08;;http://d\x1b\\{A}",
        f"\x1b\x00]8;;http://e\x1b\\{A}",
        f"\x1b]8;;http://f\x18g{A}",
        f"\x1b]8;;http://j\x1b\\{A}\x1b]8;;\x18\x1b]8;;http://k\x1b\\{B}",
        f"\x1b]8;;http://l\x1b\\{A}\x1b]80;;x\x1b\\{B}\x1b]8;;\x1b\\{C}",
        f"\x1b]8;;http://m\x07{A}\x1b]8;;http://n\x9c{B}\x9d8;;\x1b\\{C}",
    ]
    for text, cells in zip(cases, xterm_cells(cases), strict=True):
        ours = _ours(text)
        printed = [cell for cell in cells if cell[0] in POOL]
        assert printed
        assert [(char, ours.get(char)) for char, _ in printed] == printed, text


def test_a_close_with_parameters_closes_unlike_xterm_js() -> None:
    text = f"\x1b]8;;http://a\x1b\\{A}\x1b]8;id=x;\x1b\\{B}"
    assert [(found.url, found.text) for found in iter_links(text)] == [("http://a", A)]
    assert _terminal(text) == [(A, "http://a"), (B, "http://a")]


def test_del_inside_the_uri_is_dropped_unlike_xterm_js() -> None:
    text = f"\x1b]8;;http://h\x7fi\x1b\\{A}"
    assert [found.url for found in iter_links(text)] == ["http://hi"]
    assert _terminal(text) == [(A, "http://h\x7fi")]


def test_an_escape_inside_the_sequence_drops_it_unlike_xterm_js() -> None:
    text = f"\x1b]8;;http://o\x1bx{A}"
    assert list(iter_links(text)) == []
    assert _terminal(text) == [(A, "http://o")]


@pytest.mark.parametrize("size", [2084, 5000, 100_000])
def test_a_uri_longer_than_vte_allows_is_read_like_xterm_js(size: int) -> None:
    url = "http://a/" + "h" * size
    text = f"\x1b]8;;{url}\x1b\\{A}"
    assert [found.url for found in iter_links(text)] == [url]
    assert _terminal(text) == [(A, url)]


def test_an_id_longer_than_vte_allows_is_read_like_xterm_js() -> None:
    text = f"\x1b]8;id={'i' * 251};http://a/\x1b\\{A}"
    assert [found.id for found in iter_links(text)] == ["i" * 251]
    assert _terminal(text) == [(A, "http://a/")]
