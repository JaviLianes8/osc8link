"""Run the JavaScript reference implementations the oracle tests compare against.

The packages are installed by `python scripts/fetch_upstream.py` into the ignored
tests/upstream/node folder at the versions pinned in tests/upstream/MANIFEST.json; the
tests skip while node or the packages are absent.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MODULES = HERE.parent / "upstream" / "node" / "node_modules"
MANIFEST = HERE.parent / "upstream" / "MANIFEST.json"


def _node(package: str) -> str:
    """Return the node executable once package is installed at its pinned version."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    pinned = json.loads(MANIFEST.read_text(encoding="utf-8"))["npm"][package]["version"]
    installed = MODULES / package / "package.json"
    if not installed.is_file():
        pytest.skip(f"{package} is not installed; run python scripts/fetch_upstream.py")
    version = json.loads(installed.read_text(encoding="utf-8"))["version"]
    assert version == pinned, f"{package} {version} installed, {pinned} pinned"
    return node


def xterm_cells(texts: Sequence[str]) -> list[list[tuple[str, str | None]]]:
    """Return, per text, each printed cell of @xterm/headless as (character, link URI)."""
    node = _node("@xterm/headless")
    result = subprocess.run(
        [node, str(HERE / "xterm_cells.cjs"), str(MODULES)],
        input=json.dumps(list(texts)).encode("ascii"),
        capture_output=True,
        check=True,
        timeout=240,
    )
    return [[(char, uri) for char, uri in cells] for cells in json.loads(result.stdout)]


def node_supports_hyperlinks(env: Mapping[str, str], platform: str, tty: bool) -> tuple[bool, bool]:
    """Run supports-hyperlinks in a node process whose environment is exactly env.

    Returns its answer and whether its colour check (supports-color) passed.
    """
    node = _node("supports-hyperlinks")
    full = dict(env)
    if os.name == "nt":
        # Node cannot start on Windows without it; the package never reads it.
        full["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    result = subprocess.run(
        [node, str(HERE / "detect.mjs"), str(MODULES), platform, "1" if tty else "0"],
        env=full,
        capture_output=True,
        check=True,
        timeout=60,
    )
    answer = json.loads(result.stdout)
    assert isinstance(answer["hyperlinks"], bool)
    assert isinstance(answer["color"], bool)
    return answer["hyperlinks"], answer["color"]
