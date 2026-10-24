"""Guess from the environment whether a terminal shows OSC 8 hyperlinks."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping
from typing import TextIO

from ._errors import exact

# The spec says a terminal cannot be asked, so this reads the environment, following the
# rules of the `supports-hyperlinks` package plus the terminals that set a TERM of their own.
_TERMS = frozenset({"alacritty", "xterm-kitty", "foot", "foot-extra", "xterm-ghostty", "wezterm"})
_ALWAYS = frozenset({"ghostty", "zed", "Orca", "WarpTerminal"})
# parseInt skips JavaScript white space and line terminators, then reads ASCII digits only.
_JS_SPACE = "\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_LEADING_INT = re.compile(f"[{_JS_SPACE}]*([+-]?)([0-9]+)")


def supports_hyperlinks(
    stream: TextIO | None = None,
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> bool:
    """Report whether stream is a terminal that is known to show OSC 8 hyperlinks.

    stream defaults to sys.stdout, env to os.environ and platform to sys.platform.
    `FORCE_HYPERLINK=1` forces True and `FORCE_HYPERLINK=0` forces False. Otherwise the
    stream must be a TTY, `TERM` must not be `dumb` and colour must not be turned off with
    `FORCE_COLOR=0` or `false`; then Windows Terminal (`WT_SESSION`, checked first) says
    True, CI services and other Windows consoles say False, and iTerm2 3.1+, WezTerm, VS
    Code 1.72+, Ghostty, VTE (except `VTE_VERSION` 5000 or 0.50.0), Alacritty, kitty and
    foot are recognised. Numbers in the environment are read the way JavaScript's parseInt
    reads them, as the `supports-hyperlinks` package does. An environment value that is not
    a str counts as unset and a stream whose isatty fails is not a TTY; a platform that is
    not a str raises TypeError.

    >>> import io
    >>> supports_hyperlinks(io.StringIO(), env={})
    False
    >>> supports_hyperlinks(io.StringIO(), env={"FORCE_HYPERLINK": "1"})
    True
    """
    platform = sys.platform if platform is None else exact("platform", platform)
    values = os.environ if env is None else env
    env = {key: str.__str__(value) for key, value in values.items() if isinstance(value, str)}
    force = env.get("FORCE_HYPERLINK", "")
    if force:
        return _leading_int(force) != 0
    colour = env.get("FORCE_COLOR")
    if colour is not None and (colour == "false" or _leading_int(colour) == 0):
        return False
    if env.get("TERM") == "dumb":
        return False
    if not _isatty(sys.stdout if stream is None else stream):
        return False
    if "WT_SESSION" in env:
        return True
    if platform == "win32" or env.get("CI") or env.get("TEAMCITY_VERSION"):
        return False
    program = env.get("TERM_PROGRAM", "")
    if program:
        known = _program(program, env.get("TERM_PROGRAM_VERSION", ""), env)
        if known is not None:
            return known
    vte = env.get("VTE_VERSION", "")
    if vte:
        # 0.50.0 crashes on some links. VTE writes it as "5000"; the package checks only
        # "0.50.0", and other spellings are read as numbers, as the package reads them.
        if vte in ("5000", "0.50.0"):
            return False
        major, minor, _ = _version(vte)
        return major > 0 or minor >= 50
    return env.get("TERM", "") in _TERMS


def _program(program: str, version: str, env: Mapping[str, str]) -> bool | None:
    major, minor, _ = _version(version)
    if program == "iTerm.app":
        return major > 3 or (major == 3 and minor >= 1)
    if program == "WezTerm":
        nix = re.fullmatch(r"0-unstable-([0-9]{4}-[0-9]{2}-[0-9]{2})", version)
        if nix:
            return nix.group(1) >= "2020-06-20"
        return major >= 20200620
    if program == "vscode":
        # Cursor is a VS Code fork with its own 0.x versions.
        return bool(env.get("CURSOR_TRACE_ID")) or major > 1 or (major == 1 and minor >= 72)
    if program in _ALWAYS:
        return True
    return None


def _version(text: str) -> tuple[int, int, int]:
    """Read "3.1.0" as (3, 1, 0) and the dotless "4601" as (0, 46, 1); 0 when unreadable."""
    packed = re.fullmatch(r"([0-9]{1,2})([0-9]{2})", text)
    if packed:
        return 0, int(packed.group(1)), int(packed.group(2))
    parts = [_leading_int(part) for part in text.split(".")] + [None, None, None]
    major, minor, patch = (0 if part is None else part for part in parts[:3])
    return major, minor, patch


def _leading_int(text: str) -> int | None:
    """Read leading ASCII digits like JavaScript's parseInt; huge values are capped."""
    match = _LEADING_INT.match(text)
    if match is None:
        return None
    digits = match.group(2).lstrip("0") or "0"
    value = int(digits) if len(digits) <= 18 else 10**18
    return -value if match.group(1) == "-" else value


def _isatty(stream: TextIO | None) -> bool:
    try:
        return stream is not None and bool(stream.isatty())
    except Exception:
        # Whatever went wrong, a stream that cannot answer is not a terminal to write to.
        return False
