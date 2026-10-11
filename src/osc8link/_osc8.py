"""Build, detect and strip OSC 8 terminal hyperlinks."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import NamedTuple

_OSC = "\x1b]"
_ST = "\x1b\\"

# Open:  ESC ] 8 ; params ; URI  (ESC-backslash | BEL)
# Close: ESC ] 8 ;        ;      (ESC-backslash | BEL)
# Parameters and URI never carry ESC or BEL; either terminator is accepted on parse.
_TERMINATOR = r"(?:\x1b\\|\x07)"
_ANY_SEQUENCE = re.compile(r"\x1b\]8;[^\x1b\x07]*" + _TERMINATOR)
_OPEN_WITH_URI = re.compile(r"\x1b\]8;[^;\x1b\x07]*;[^\x1b\x07]+" + _TERMINATOR)
_LINK = re.compile(
    r"\x1b\]8;[^;\x1b\x07]*;([^\x1b\x07]+)" + _TERMINATOR + r"(.*?)\x1b\]8;;" + _TERMINATOR,
    re.DOTALL,
)


class Link(NamedTuple):
    """A hyperlink found in text: the target url and the visible text."""

    url: str
    text: str


def link(url: str, text: str, *, id: str | None = None) -> str:
    """Wrap text in an OSC 8 hyperlink to url, emitting ESC-backslash terminators."""
    params = f"id={id}" if id is not None else ""
    return f"{_OSC}8;{params};{url}{_ST}{text}{_OSC}8;;{_ST}"


def strip(s: str) -> str:
    """Return s with every OSC 8 sequence removed and the visible text kept."""
    return _ANY_SEQUENCE.sub("", s)


def contains_link(s: str) -> bool:
    """Report whether s holds at least one OSC 8 hyperlink."""
    return _OPEN_WITH_URI.search(s) is not None


def iter_links(s: str) -> Iterator[Link]:
    """Yield each complete OSC 8 hyperlink as (url, text), in order of appearance."""
    for match in _LINK.finditer(s):
        yield Link(match.group(1), match.group(2))
