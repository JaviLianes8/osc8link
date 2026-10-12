"""Find OSC 8 sequences in text and read the links they draw."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

# Read the way the DEC parser that xterm and VTE follow reads it. OSC is ESC ] (C0 controls
# between the two are executed and DEL is ignored, so they do not break the opener) or the
# C1 byte U+009D. ST is ESC \ or U+009C, and XTerm's BEL is accepted everywhere. Inside the
# payload ESC, CAN, SUB and every C1 control abort the string, so a sequence cut short by
# one of them (or by the end of the text) draws nothing and is not a link.
_ABORT = r"\x07\x18\x1a\x1b\x80-\x9f"
_SEQUENCE = re.compile(
    r"(?:\x1b(?P<c0>[\x00-\x17\x19\x1c-\x1f\x7f]*)\]|\x9d)"
    rf"0*8(?=[;{_ABORT}]|\Z)(?P<payload>[^{_ABORT}]*)(?P<end>\x1b\\|\x07|\x9c)?"
)
# C0 controls inside an OSC string are ignored by the terminal.
_IGNORED = re.compile(r"[\x00-\x1f]")


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
    """Return s with every OSC 8 sequence removed and the visible text kept.

    Sequences cut short (by ESC, CAN, SUB, a C1 control or the end of s) are removed up to
    the byte that cut them, as a terminal would hide them.
    """
    return _SEQUENCE.sub(lambda match: (match.group("c0") or "").replace("\x7f", ""), s)


def contains_link(s: str) -> bool:
    """Report whether s holds an OSC 8 sequence that opens a link to a non-empty URI."""
    return any(_open(match) is not None for match in _SEQUENCE.finditer(s))


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
        if _target(match) is None:
            continue
        if current is not None and "".join(pieces):
            yield Link(current.url, "".join(pieces), current.id, current.params)
        current = _open(match)
        pieces = []
    pieces.append(s[position:])
    if current is not None and "".join(pieces):
        yield Link(current.url, "".join(pieces), current.id, current.params)


def _target(match: re.Match[str]) -> str | None:
    """Return the URI of a complete, well-formed sequence (empty for a close), else None."""
    if match.group("end") is None:
        return None
    payload = _IGNORED.sub("", match.group("payload"))
    # The scanner only matches an 8 followed by ";" or the terminator, so a payload is
    # empty or starts with ";"; it is well formed when a second ";" ends the parameters.
    if ";" not in payload[1:]:
        return None
    return payload[1:].split(";", 1)[1]


def _open(match: re.Match[str]) -> Link | None:
    """Return the link a sequence opens, or None for a close or a malformed sequence."""
    target = _target(match)
    if not target:
        return None
    raw = _IGNORED.sub("", match.group("payload"))[1:].split(";", 1)[0]
    params = tuple(
        (key, value) for key, sep, value in (item.partition("=") for item in raw.split(":")) if sep
    )
    found = next((value for key, value in params if key == "id"), "")
    return Link(target, "", found or None, params)


def unfinished_tail(s: str) -> int:
    """Return where an OSC 8 sequence still open at the end of s starts, else len(s).

    A stream filter holds that tail back until more input arrives. An open sequence has no
    ESC or C1 control after its opener, so only the last one can start it.
    """
    start = max(s.rfind("\x1b"), s.rfind("\x9d"))
    match = _SEQUENCE.match(s, start) if start >= 0 else None
    if match and match.group("end") is None and match.end() == len(s):
        return start
    return len(s)
