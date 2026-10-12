"""The osc8link command line: build a link, strip or list links, check the terminal."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ._build import Terminator, link
from ._detect import supports_hyperlinks
from ._sequences import iter_links, strip

# Filters read and write UTF-8; any other byte passes through unchanged.
_ENCODING = "utf-8"
_ERRORS = "surrogateescape"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osc8link", description="Build, strip and list OSC 8 terminal hyperlinks."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("link", help="print a hyperlink to URL showing TEXT")
    build.add_argument("url")
    build.add_argument("text", nargs="?", help="visible text (default: the url)")
    build.add_argument("--id", help="id that joins split pieces into one link")
    build.add_argument("--bel", action="store_true", help="end sequences with BEL")
    commands.add_parser("strip", help="copy stdin to stdout without hyperlinks")
    commands.add_parser("list", help="print URL<TAB>TEXT for each hyperlink on stdin")
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
            _write(strip(_read()))
        else:
            for found in iter_links(_read()):
                flat = " ".join(found.text.splitlines())
                _write(f"{found.url}\t{flat.replace(chr(9), ' ')}\n")
    except ValueError as error:
        print(f"osc8link: {error}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # The reader went away (`osc8link list | head`): nothing left to report.
        return 0
    return 0


def _read() -> str:
    return sys.stdin.buffer.read().decode(_ENCODING, _ERRORS)


def _write(text: str) -> None:
    sys.stdout.buffer.write(text.encode(_ENCODING, _ERRORS))
    sys.stdout.buffer.flush()
