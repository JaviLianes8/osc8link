"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from osc8link import auto_link, contains_link, encode_url, iter_links, link, strip
from osc8link import supports_hyperlinks
reveal_type(link("u", "t"))
reveal_type(auto_link("u", "t"))
reveal_type(strip("s"))
reveal_type(contains_link("s"))
reveal_type(next(iter_links("s")).id)
reveal_type(next(iter_links("s")).params)
reveal_type(supports_hyperlinks(env={}, platform="linux"))
reveal_type(encode_url("u"))
link("u", "t", terminator="esc")
link(b"u", "t")
link("u", "t", "id")
supports_hyperlinks(env={"A": 1})
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    args = ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    try:
        from mypy import api
    except ImportError:
        # The interpreter running pytest may lack mypy while the one on PATH has it.
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        result = subprocess.run([program, *args], capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def test_functions_return_plain_types(mypy_output: str) -> None:
    assert [_revealed(mypy_output, line) for line in (4, 5, 6, 7, 10, 11)] == [
        "str",
        "str",
        "str",
        "bool",
        "bool",
        "str",
    ]


def test_link_fields_are_typed(mypy_output: str) -> None:
    assert _revealed(mypy_output, 8) == "str | None"
    assert _revealed(mypy_output, 9) == "tuple[tuple[str, str], ...]"


def test_misuse_is_rejected(mypy_output: str) -> None:
    for line, code in ((12, "arg-type"), (13, "arg-type"), (14, "call-arg"), (15, "dict-item")):
        assert re.search(rf"snippet\.py:{line}: error: .*\[{code}\]", mypy_output), mypy_output


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return match.group(1).replace("builtins.", "")
