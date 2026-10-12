from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "data"


def read_data(name: str) -> str:
    """Return a pinned third-party file as text, keeping undecodable bytes as surrogates.

    The files stay out of the sdist, so outside a git checkout their tests are skipped; in a
    checkout a missing file is a failure.
    """
    path = DATA / name
    if not path.is_file() and not (ROOT / ".git").exists():
        pytest.skip(f"{name} ships only with the git repository")
    return path.read_bytes().decode("utf-8", "surrogateescape")


@pytest.fixture(scope="session")
def spec_text() -> str:
    """The OSC 8 spec gist, see test_spec.py for its source."""
    return read_data("egmontkob-hyperlinks.md")


@pytest.fixture(scope="session")
def vte_demo() -> str:
    """The VTE hyperlink test file, see test_vte_demo.py for its source."""
    return read_data("vte-hyperlink-demo.txt")
