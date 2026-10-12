from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def read_upstream(name: str) -> str:
    """Return a third-party test file as text, undecodable bytes kept as surrogates.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    entry = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))[name]
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{name} differs from MANIFEST"
    return body.decode("utf-8", "surrogateescape")


@pytest.fixture(scope="session")
def spec_text() -> str:
    """The OSC 8 spec gist, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("egmontkob-hyperlinks.md")


@pytest.fixture(scope="session")
def vte_demo() -> str:
    """The VTE hyperlink test file, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("vte-hyperlink-demo.txt")
