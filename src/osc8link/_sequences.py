"""Find OSC 8 sequences in text and read the links they draw."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

# OSC is ESC ] or the C1 byte U+009D; ST is ESC \ or U+009C, and XTerm's BEL is accepted
# everywhere, so a sequence may mix the two forms. ESC inside the payload aborts the string
# (it starts a new escape), so it never belongs to a sequence.
_OPENER = r"(?:\x1b\]|\x9d)"
_TERMINATOR = r"(?:\x1b\\|\x07|\x9c)"
_SEQUENCE = re.compile(_OPENER + r"8(?=[;\x1b\x07\x9c])([^\x1b\x07\x9c]*)" + _TERMINATOR)


@dataclass(frozen=True)
class Link:
    """A hyperlink found in text.

    `url` is the target as written, `text` the visible text (it may hold other escape
    sequences such as colours), `id` the `id` parameter or None when absent or empty, and
    `params` every `key=value` parameter in order. A Link unpacks as `(url, text)`.
    """

    url: str
    text: str
    id: str | None = None
    params: tuple[tuple[str, str], ...] = ()

    def __iter__(self) -> Iterator[str]:
        yield self.url
        yield self.text


def strip(s: str) -> str:
    """Return s with every OSC 8 sequence removed and the visible text kept."""
    return _SEQUENCE.sub("", s)


def contains_link(s: str) -> bool:
    """Report whether s holds an OSC 8 sequence that opens a link to a non-empty URI."""
    return any(_open(match.group(1)) is not None for match in _SEQUENCE.finditer(s))


def iter_links(s: str) -> Iterator[Link]:
    """Yield each hyperlink in s, in order of appearance.

    Follows the terminal state machine of the spec: an OSC 8 with a URI starts a link (and
    ends any open one), an OSC 8 without a URI ends it, and a link still open at the end of
    s runs to the end. Links with no visible text are skipped.
    """
    current: Link | None = None
    pieces: list[str] = []
    position = 0
    for match in _SEQUENCE.finditer(s):
        pieces.append(s[position : match.start()])
        position = match.end()
        target = _target(match.group(1))
        if target is None:
            continue
        if current is not None and "".join(pieces):
            yield Link(current.url, "".join(pieces), current.id, current.params)
        current = _open(match.group(1))
        pieces = []
    pieces.append(s[position:])
    if current is not None and "".join(pieces):
        yield Link(current.url, "".join(pieces), current.id, current.params)


def _target(payload: str) -> str | None:
    """Return the URI of a well-formed payload (empty for a close), None if malformed."""
    if not payload.startswith(";") or ";" not in payload[1:]:
        return None
    return payload[1:].split(";", 1)[1]


def _open(payload: str) -> Link | None:
    """Return the link a payload opens, or None for a close or a malformed payload."""
    target = _target(payload)
    if not target:
        return None
    raw = payload[1:].split(";", 1)[0]
    params = tuple(
        (key, value)
        for key, sep, value in (item.partition("=") for item in raw.split(":") if item)
        if sep
    )
    found = next((value for key, value in params if key == "id"), "")
    return Link(target, "", found or None, params)
