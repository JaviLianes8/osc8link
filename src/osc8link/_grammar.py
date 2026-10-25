"""The shape of an OSC 8 sequence, as VTE's parser reads it."""

from __future__ import annotations

import re

# OSC is ESC ] (C0 controls between the two are executed and DEL is ignored, so they do not
# break the opener) or the C1 byte U+009D. ST is ESC \ or U+009C, and XTerm's BEL is
# accepted everywhere. Inside the string, the command number included, C0 controls other
# than BEL, CAN, SUB and ESC and DEL are ignored, while ESC, CAN, SUB and every C1 control
# abort it, so a sequence cut short by one of them (or by the end of the text) draws
# nothing and is not a link. Unlike VTE, 7-bit and 8-bit openers and terminators may be
# mixed, as in xterm.js.
ABORT = r"\x07\x18\x1a\x1b\x80-\x9f"
BETWEEN = r"\x00-\x17\x19\x1c-\x1f\x7f"
IGNORED = r"\x00-\x06\x08-\x17\x19\x1c-\x1f\x7f"
SEQUENCE = re.compile(
    rf"(?:\x1b(?P<c0>[{BETWEEN}]*)\]|\x9d)[0{IGNORED}]*8(?=[{IGNORED}]*(?:[;{ABORT}]|\Z))"
    rf"(?P<payload>[^{ABORT}]*)(?P<end>\x1b\\|\x07|\x9c)?"
)
# The start of an opener that more text could still complete.
PREFIX = re.compile(rf"(?:\x1b[{BETWEEN}]*(?:\][0{IGNORED}]*)?|\x9d[0{IGNORED}]*)\Z")
# What may follow an unfinished tail without changing what it is: more of the payload,
# more ignored controls after the 8, more of the number, more controls before the `]`.
KEEP_PAYLOAD = re.compile(f"[^{ABORT}]*")
KEEP_IGNORED = re.compile(f"[{IGNORED}]*")
KEEP_NUMBER = re.compile(f"[0{IGNORED}]*")
KEEP_BETWEEN = re.compile(f"[{BETWEEN}]*")
