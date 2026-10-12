"""Guess from the environment whether a terminal shows OSC 8 hyperlinks."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping
from typing import TextIO

# The spec says a terminal cannot be asked, so this reads the environment, following the
# rules of the `supports-hyperlinks` package plus the terminals that set a TERM of their own.
_TERMS = frozenset({"alacritty", "xterm-kitty", "foot", "foot-extra", "xterm-ghostty", "wezterm"})
_ALWAYS = frozenset({"ghostty", "zed", "Orca", "WarpTerminal"})


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
    `FORCE_COLOR=0`; then Windows Terminal, iTerm2 3.1+, WezTerm, VS Code 1.72+, Ghostty,
    VTE 0.50.1+, Alacritty, kitty and foot are recognised. CI services give False.
    """
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    force = env.get("FORCE_HYPERLINK", "")
    if force:
        return _leading_int(force) != 0
    if env.get("FORCE_COLOR", "") in ("0", "false") or env.get("TERM") == "dumb":
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
        # 0.50.0 crashes on some links; VTE writes it as "5000".
        if vte in ("5000", "0.50.0"):
            return False
        major, minor, _ = _version(vte)
        return major > 0 or minor >= 50
    return env.get("TERM", "") in _TERMS


def _program(program: str, version: str, env: Mapping[str, str]) -> bool | None:
    major, minor, _ = _version(version)
    if program == "iTerm.app":
        return minor >= 1 if major == 3 else major > 3
    if program == "WezTerm":
        nix = re.fullmatch(r"0-unstable-(\d{4}-\d{2}-\d{2})", version)
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
    """Read "3.1.0" as (3, 1, 0) and the dotless "4601" as (0, 46, 1); -1 when unreadable."""
    packed = re.fullmatch(r"(\d{1,2})(\d{2})", text)
    if packed:
        return 0, int(packed.group(1)), int(packed.group(2))
    parts = [_leading_int(part) for part in text.split(".")] + [None, None, None]
    major, minor, patch = (-1 if part is None else part for part in parts[:3])
    return major, minor, patch


def _leading_int(text: str) -> int | None:
    match = re.match(r"\s*([+-]?\d+)", text)
    return int(match.group(1)) if match else None


def _isatty(stream: TextIO | None) -> bool:
    try:
        return stream is not None and stream.isatty()
    except (AttributeError, ValueError):
        return False
