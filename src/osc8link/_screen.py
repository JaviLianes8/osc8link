"""Remove OSC 8 sequences without changing how a terminal reads the text around them."""

from __future__ import annotations

import re

from ._grammar import SEQUENCE

# ESC, CAN, SUB and every C1 control act the same in any parser state, so whether text
# leaves an escape sequence or control string unfinished depends only on what follows the
# last of them.
_INTRODUCER = re.compile(r"[\x18\x1a\x1b\x80-\x9f]")
# Executed C0 controls and DEL leave the state as it is; BEL is kept because it ends an OSC.
_QUIET = re.compile(r"[\x00-\x06\x08-\x17\x19\x1c-\x1f\x7f]")
_C1 = {"\x9b": "\x1b[", "\x9d": "\x1b]", "\x90": "\x1bP", "\x98": "\x1bX", "\x9e": "\x1b^"}
_C1["\x9f"] = "\x1b_"
# An escape waiting for its final byte, a CSI waiting for its final byte, an OSC waiting
# for its terminator, or a DCS, SOS, PM or APC string waiting for ST.
_PENDING = re.compile(
    r"\x1b\x07*(?:(?P<int>[\x20-\x2f][\x07\x20-\x2f]*)|(?P<csi>\[)[\x07\x20-\x3f]*"
    r"|(?P<osc>\])[^\x07]*|(?P<str>[PX^_]).*)?",
    re.DOTALL,
)
# CAN cancels any escape sequence or control string and does nothing in the ground state.
CANCEL = "\x18"


def carry(state: str, text: str) -> str:
    """Return the unfinished sequence that state followed by text leaves, "" for none.

    The result is a short stand-in ("\\x1b", "\\x1b ", "\\x1b[", "\\x1b]" or "\\x1bP") that
    behaves like the real tail for any text that follows.
    """
    last = -1
    for found in _INTRODUCER.finditer(text):
        last = found.start()
    if last >= 0:
        state, text = "", text[last:]
    elif not state:
        return ""
    tail = state + text
    if not tail:
        return ""
    tail = _C1.get(tail[0], tail[0]) + tail[1:]
    match = _PENDING.fullmatch(_QUIET.sub("", tail))
    if match is None:
        return ""
    for group, stand_in in (("int", "\x1b "), ("csi", "\x1b["), ("osc", "\x1b]"), ("str", "\x1bP")):
        if match.group(group) is not None:
            return stand_in
    return "\x1b"


def strip_part(s: str, state: str = "") -> tuple[str, str]:
    """Strip s, which follows text that left state unfinished; return it and the new state.

    Removing a sequence joins the text on both sides. When the opener of a removed
    sequence was also what ended an unfinished escape sequence or control string before
    it, a CAN takes its place, so the text after it cannot complete what came before.
    """
    pieces: list[str] = []
    position = 0
    for match in SEQUENCE.finditer(s):
        kept = s[position : match.start()]
        pieces.append(kept)
        if carry(state, kept):
            pieces.append(CANCEL)
        pieces.append((match.group("c0") or "").replace("\x7f", ""))
        state, position = "", match.end()
    pieces.append(s[position:])
    return "".join(pieces), carry(state, s[position:])
