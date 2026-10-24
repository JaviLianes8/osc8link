"""Fetch the third-party test material listed in tests/upstream/MANIFEST.json.

None of it is part of the repository. Its tests skip until this script has fetched it:

- "files": spec text and VTE sources, each checked against the size and sha256 listed;
- "npm": the JavaScript reference implementations used as oracles, installed with npm
  (scripts disabled) into tests/upstream/node at the pinned versions, each checked against
  the integrity hash listed. Skipped with a note when npm is not installed.

    python scripts/fetch_upstream.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "tests" / "upstream"


def fetch_files(entries: dict[str, dict[str, object]]) -> int:
    failed = 0
    for name, entry in entries.items():
        with urllib.request.urlopen(str(entry["url"]), timeout=60) as response:
            body = response.read()
        digest = hashlib.sha256(body).hexdigest()
        if len(body) != entry["size"] or digest != entry["sha256"]:
            print(f"{name}: got {len(body)} bytes, sha256 {digest}; manifest differs")
            failed += 1
            continue
        (FOLDER / name).write_bytes(body)
        print(f"{name}: ok")
    return failed


def install_npm(entries: dict[str, dict[str, str]]) -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("npm is not installed: the oracle tests will skip")
        return 0
    target = FOLDER / "node"
    target.mkdir(exist_ok=True)
    package = {
        "name": "osc8link-oracles",
        "private": True,
        "dependencies": {name: entry["version"] for name, entry in entries.items()},
    }
    (target / "package.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    flags = ["--ignore-scripts", "--no-audit", "--no-fund", "--save-exact"]
    subprocess.run([npm, "install", *flags], cwd=target, check=True)
    lock = json.loads((target / "package-lock.json").read_text(encoding="utf-8"))
    failed = 0
    for name, entry in entries.items():
        found = lock["packages"].get(f"node_modules/{name}", {})
        same = (found.get("version"), found.get("integrity")) == (
            entry["version"],
            entry["integrity"],
        )
        print(f"{name} {found.get('version')}: {'ok' if same else 'differs from MANIFEST'}")
        failed += not same
    return failed


def main() -> int:
    manifest = json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
    failed = fetch_files(manifest["files"]) + install_npm(manifest["npm"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
