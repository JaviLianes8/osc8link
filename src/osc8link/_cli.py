"""The osc8link command line: build a link, strip or list links, check the terminal."""

from __future__ import annotations

import argparse
import errno
import os
import re
import sys
from collections.abc import Iterable, Iterator, Sequence

from . import __version__
from ._build import Terminator, link
from ._detect import supports_hyperlinks
from ._screen import strip_part
from ._sequences import iter_links, keep_pattern, unfinished_tail

# Filters read and write UTF-8; any other byte passes through unchanged.
_ENCODING = "utf-8"
_ERRORS = "surrogateescape"
# `strip` holds back an open sequence while it is shorter than this many characters.
_HOLD_LIMIT = 1 << 16
# Every C0 and C1 control, DEL, the backslash and every byte that is not UTF-8 (read as
# U+DC80 to U+DCFF), shown escaped by `list`: a raw 0x9B is a CSI on an 8-bit terminal.
_UNSAFE = re.compile(r"[\x00-\x1f\x7f-\x9f\\\udc80-\udcff]")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osc8link", description="Build, strip and list OSC 8 terminal hyperlinks."
    )
    parser.add_argument("--version", action="version", version=f"osc8link {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("link", help="print a hyperlink to URL showing TEXT")
    build.add_argument("url", metavar="URL")
    build.add_argument("text", nargs="?", metavar="TEXT", help="visible text (default: URL)")
    build.add_argument("--id", help="id that joins split pieces into one link")
    build.add_argument("--bel", action="store_true", help="end sequences with BEL")
    commands.add_parser("strip", help="copy stdin to stdout without hyperlinks, line by line")
    commands.add_parser(
        "list", help="print URL<TAB>TEXT for each hyperlink on stdin, controls escaped"
    )
    commands.add_parser("supports", help="exit 0 if stdout shows hyperlinks, 1 if not")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with argv (default: sys.argv[1:]) and return the exit code."""
    args = _parser().parse_args(argv)
    closed = _closed(args.command)
    if closed:
        # Started with no stdin or stdout at all (`osc8link list <&-`, or under pythonw).
        if sys.stderr is not None:
            print(f"osc8link: {closed} is closed", file=sys.stderr)
        return 2
    try:
        if args.command == "supports":
            return 0 if supports_hyperlinks(sys.stdout) else 1
        if args.command == "link":
            text = args.url if args.text is None else args.text
            terminator: Terminator = "bel" if args.bel else "st"
            _write(link(args.url, text, id=args.id, terminator=terminator) + "\n")
        elif args.command == "strip":
            for chunk in _strip_stream(_lines()):
                _write(chunk)
        else:
            found = iter_links("".join(_lines()))
            _write("".join(f"{_escape(item.url)}\t{_escape(item.text)}\n" for item in found))
    except ValueError as error:
        print(f"osc8link: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        # The reader went away (`osc8link list | head`); Windows reports it as EINVAL.
        if not isinstance(error, BrokenPipeError) and error.errno != errno.EINVAL:
            raise
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    return 0


def _strip_stream(lines: Iterable[str]) -> Iterator[str]:
    """Strip line by line, holding back a sequence that is still open at a line's end.

    A held tail is scanned again only when a line could change it, so a long open sequence
    costs linear time; a sequence that never ends is let go at the hold limit (a terminal
    swallows it anyway).
    """
    held: list[str] = []
    size = 0
    keep = None
    state = ""
    for line in lines:
        if keep is not None and size + len(line) < _HOLD_LIMIT and keep.fullmatch(line):
            held.append(line)
            size += len(line)
            continue
        pending = "".join(held) + line
        cut = unfinished_tail(pending) if len(pending) < _HOLD_LIMIT else len(pending)
        done, state = strip_part(pending[:cut], state)
        yield done
        held, size = [pending[cut:]], len(pending) - cut
        keep = keep_pattern(held[0]) if size else None
    yield strip_part("".join(held), state)[0]


def _escape(text: str) -> str:
    return _UNSAFE.sub(lambda match: _ESCAPES.get(match.group(), _hex(match.group())), text)


def _hex(char: str) -> str:
    code = ord(char)
    return f"\\x{code - 0xDC00 if code >= 0xDC00 else code:02x}"


_ESCAPES = {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}


def _closed(command: str) -> str | None:
    """Name the standard stream the command needs but the process was started without."""
    if command in ("link", "strip", "list") and sys.stdout is None:
        return "stdout"
    if command in ("strip", "list") and sys.stdin is None:
        return "stdin"
    return None


def _lines() -> Iterable[str]:
    for line in sys.stdin.buffer:
        yield line.decode(_ENCODING, _ERRORS)


def _write(text: str) -> None:
    sys.stdout.buffer.write(text.encode(_ENCODING, _ERRORS))
    sys.stdout.buffer.flush()
