"""Detection checked against the package it is modelled on, supports-hyperlinks.

Seeded random environments are given to supports-hyperlinks 4.6.0 (pinned in
tests/upstream/MANIFEST.json) in a node process whose environment is exactly that one, and to
`supports_hyperlinks`. Where the package's colour check (supports-color) passes, the answers
must be equal. The documented differences are kept out of the generator and pinned in
test_detect.py: command-line flags and NETLIFY are not read, VTE_VERSION=5000 says no, the
TERM values of foot, Ghostty and WezTerm say yes, TERM=dumb says no, and no colour level is
required beyond FORCE_COLOR not being 0 or false.

RECORDED holds answers the package gave on 2026-10-24 for shapes where 0.2.0 differed;
those run without node.
"""

from __future__ import annotations

import io
import random

import pytest
from oracles import node_supports_hyperlinks

from osc8link import supports_hyperlinks

NBSP, BOM, LS = chr(0xA0), chr(0xFEFF), chr(0x2028)
ARABIC = "".join(chr(0x660 + digit) for digit in (5, 0, 0, 1))
NIX_ARABIC = "0-unstable-" + "".join(
    chr(0x660 + int(char)) if char.isdigit() else char for char in "2020-06-20"
)
NUMBERS = ["", "0", "1", "00", "-0", "+1", " 0", NBSP + "0", BOM + "1", LS + "0", "0x1", "abc"]
VALUES: dict[str, list[str]] = {
    "FORCE_HYPERLINK": [*NUMBERS, "true", "false", "9" * 30],
    "FORCE_COLOR": [*NUMBERS, "true", "false", "2", "3", "4", "-1"],
    "TERM": ["xterm-256color", "xterm", "screen", "linux", "alacritty", "xterm-kitty", "vt100"],
    "COLORTERM": ["truecolor", "24bit", ""],
    "CI": ["", "true", "0"],
    "GITHUB_ACTIONS": ["true"],
    "TEAMCITY_VERSION": ["", "9.1.2", "2023.05"],
    "TF_BUILD": ["True"],
    "AGENT_NAME": ["x"],
    "WT_SESSION": ["", "abc"],
    "TERM_PROGRAM": [
        "iTerm.app",
        "WezTerm",
        "vscode",
        "ghostty",
        "zed",
        "Orca",
        "WarpTerminal",
        "Apple_Terminal",
        "tmux",
        "Hyper",
    ],
    "TERM_PROGRAM_VERSION": [
        *NUMBERS,
        "3.1",
        "3.0.9",
        "4",
        "1.72.0",
        "1.71.9",
        "2.0",
        "20200620-1",
        "20200619-1",
        "0-unstable-2020-06-20",
        "0-unstable-2019-01-01",
        NIX_ARABIC,
        "3.1",
        NBSP + "3.1",
        "3." + NBSP + "1",
    ],
    "VTE_VERSION": [
        *NUMBERS,
        "0.50.0",
        "0.50.1",
        "0.49.9",
        "4601",
        "5001",
        "6003",
        "502",
        "05001",
        ARABIC,
        "1.0",
    ],
    "CURSOR_TRACE_ID": ["", "x"],
}
PLATFORMS = ["linux", "darwin", "freebsd", "win32"]

RECORDED: list[tuple[dict[str, str], bool]] = [
    ({"TERM": "xterm", "VTE_VERSION": "00100"}, True),
    ({"TERM": "xterm", "TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": "30100"}, True),
    ({"TERM": "xterm", "TERM_PROGRAM": "vscode", "TERM_PROGRAM_VERSION": "10072"}, True),
    ({"TERM": "xterm", "FORCE_HYPERLINK": NBSP + "0"}, False),
    ({"TERM": "xterm", "FORCE_HYPERLINK": BOM + "0"}, False),
    ({"TERM": "xterm", "FORCE_HYPERLINK": LS + "0"}, False),
    ({"TERM": "xterm", "VTE_VERSION": ARABIC}, False),
    ({"TERM": "xterm", "TERM_PROGRAM": "iTerm.app", "TERM_PROGRAM_VERSION": NBSP + "3.1"}, True),
    ({"TERM": "xterm", "VTE_VERSION": "05001"}, True),
    ({"TERM": "xterm", "VTE_VERSION": "5001"}, True),
    ({"TERM": "xterm", "VTE_VERSION": "502"}, False),
    ({"TERM": "xterm", "VTE_VERSION": "999"}, False),
    ({"TERM": "xterm", "TERM_PROGRAM": "WezTerm", "TERM_PROGRAM_VERSION": NIX_ARABIC}, False),
    (
        {
            "TERM": "xterm",
            "TERM_PROGRAM": "WezTerm",
            "TERM_PROGRAM_VERSION": "0-unstable-2020-06-20",
        },
        True,
    ),
]


class Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def _ours(env: dict[str, str], platform: str, tty: bool) -> bool:
    return supports_hyperlinks(Tty() if tty else io.StringIO(), env=env, platform=platform)


@pytest.mark.parametrize(("env", "expected"), RECORDED)
def test_recorded_answers_of_the_package(env: dict[str, str], expected: bool) -> None:
    assert _ours(env, "linux", True) is expected


@pytest.mark.parametrize(("env", "expected"), RECORDED)
def test_the_recorded_answers_are_what_the_package_says(
    env: dict[str, str], expected: bool
) -> None:
    assert node_supports_hyperlinks(env, "linux", True) == (expected, True)


def _environment(rng: random.Random) -> dict[str, str]:
    keys = rng.sample(sorted(VALUES), rng.randrange(1, 6))
    if rng.random() < 0.8:
        keys.append("TERM")
    return {key: rng.choice(VALUES[key]) for key in keys}


@pytest.mark.parametrize("seed", [7, 8])
def test_random_environments_agree_with_the_package(seed: int) -> None:
    rng = random.Random(seed)
    compared = said_yes = 0
    for _ in range(200):
        env, platform, tty = _environment(rng), rng.choice(PLATFORMS), rng.random() < 0.85
        theirs, colour = node_supports_hyperlinks(env, platform, tty)
        ours = _ours(env, platform, tty)
        if colour or env.get("FORCE_HYPERLINK"):
            assert ours is theirs, (env, platform, tty)
            compared += 1
            said_yes += theirs
        elif not tty:
            assert ours is False, env
    assert compared > 100
    assert said_yes > 20
