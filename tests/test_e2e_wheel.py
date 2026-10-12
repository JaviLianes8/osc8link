"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with OSC8LINK_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("OSC8LINK_E2E") != "1", reason="set OSC8LINK_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, io, pickle
import osc8link
from osc8link import Link, auto_link, contains_link, iter_links, link, strip

assert "site-packages" in osc8link.__file__, osc8link.__file__
assert importlib.metadata.version("osc8link") == osc8link.__version__
assert importlib.resources.files("osc8link").joinpath("py.typed").is_file()
built = link("https://a.test/é", "A", id="x")
assert built == "\x1b]8;id=x;https://a.test/%C3%A9\x1b\\A\x1b]8;;\x1b\\", built
switched = "\x9d8;;https://a.test\x07A\x1b]8;;https://b.test\x9cB"
assert list(iter_links(switched)) == [Link("https://a.test", "A"), Link("https://b.test", "B")]
assert strip(switched) == "AB" and contains_link(switched)
assert auto_link("https://a.test", "A", stream=io.StringIO()) == "A (https://a.test)"
found = next(iter_links(built))
assert pickle.loads(pickle.dumps(found)) == found and found.id == "x"
for bad in ({"id": "a;b"}, {"terminator": "esc"}):
    try:
        link("https://a.test", "A", **bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("osc8link-*.whl")
    (sdist,) = dist.glob("osc8link-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "osc8link/py.typed" in names
    assert not any(name.startswith("tests/") for name in names)
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout.decode()
    assert "IMPROVEMENTS-round" not in listing
    assert "tests/upstream/MANIFEST.json" in listing
    assert "egmontkob-hyperlinks.md" not in listing
    assert "vte-hyperlink-demo.txt" not in listing
    assert "tests/test_spec.py" in listing

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    script = bindir / ("osc8link.exe" if sys.platform == "win32" else "osc8link")
    cli = _run(script, "link", "https://a.test", "A", cwd=work)
    assert (cli.returncode, cli.stdout) == (0, b"\x1b]8;;https://a.test\x1b\\A\x1b]8;;\x1b\\\n")
    stripped = _run(script, "strip", cwd=work, stdin=b"x " + cli.stdout + b"\xff")
    assert stripped.stdout == b"x A\n\xff"
    listed = _run(python, "-m", "osc8link", "list", cwd=work, stdin=cli.stdout)
    assert listed.stdout == b"https://a.test\tA\n"
    assert _run(script, "link", "", cwd=work).returncode == 2
