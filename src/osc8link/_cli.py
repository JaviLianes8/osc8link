"""The osc8link command line: build a link, strip or list links, check the terminal."""

from __future__ import annotations

import argparse
import errno
import os
import re
import sys
from collections.abc import Iterable, Sequence

from ._build import Terminator, link
from ._detect import supports_hyperlinks
from ._sequences import iter_links, strip, unfinished_tail

# Filters read and write UTF-8; any other byte passes through unchanged.
_ENCODING = "utf-8"
_ERRORS = "surrogateescape"
# The longest open sequence `strip` holds back while waiting for its end.
_HOLD_LIMIT = 1 << 16
# Every C0 and C1 control, DEL and the backslash, shown escaped by `list`.
_UNSAFE = re.compile(r"[\x00-\x1f\x7f-\x9f\\]")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osc8link", description="Build, strip and list OSC 8 terminal hyperlinks."
    )
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


def _strip_stream(lines: Iterable[str]) -> Iterable[str]:
    """Strip line by line, holding back a sequence that is still open at a line's end."""
    pending = ""
    for line in lines:
        pending += line
        # A sequence that never ends is let go after a while; a terminal swallows it anyway.
        cut = unfinished_tail(pending) if len(pending) < _HOLD_LIMIT else len(pending)
        yield strip(pending[:cut])
        pending = pending[cut:]
    yield strip(pending)


def _escape(text: str) -> str:
    return _UNSAFE.sub(
        lambda match: _ESCAPES.get(match.group(), f"\\x{ord(match.group()):02x}"), text
    )


_ESCAPES = {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}


def _lines() -> Iterable[str]:
    for line in sys.stdin.buffer:
        yield line.decode(_ENCODING, _ERRORS)


def _write(text: str) -> None:
    sys.stdout.buffer.write(text.encode(_ENCODING, _ERRORS))
    sys.stdout.buffer.flush()
