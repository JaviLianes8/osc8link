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
import io
from typing import IO
def from_io(stream: IO[str]) -> bool:
    return supports_hyperlinks(stream)
def from_base(stream: io.TextIOBase) -> str:
    return auto_link("u", "t", stream=stream)
class Pane:
    def isatty(self) -> bool: return True
supports_hyperlinks(Pane())
supports_hyperlinks(5)
class Count:
    def isatty(self) -> int: return 1
supports_hyperlinks(Count())
from osc8link import SupportsIsatty
def wrap(stream: SupportsIsatty | None = None) -> str:
    return auto_link("u", "t", stream=stream)
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


def test_any_object_with_isatty_is_a_stream(mypy_output: str) -> None:
    # IO[str], io.TextIOBase and a class of one's own all have isatty(), which is all
    # detection calls; an object without it is still rejected.
    errors = re.findall(r"snippet\.py:(\d+): error:", mypy_output)
    assert [line for line in errors if 16 <= int(line) <= 24] == [], mypy_output
    assert re.search(r"snippet\.py:25: error: .*\[arg-type\]", mypy_output), mypy_output


def test_isatty_is_typed_to_return_a_bool(mypy_output: str) -> None:
    # At run time any answer is read by its truth value, but the declared type is bool,
    # so an isatty returning an int is rejected; widening it later breaks nobody.
    assert re.search(r"snippet\.py:28: error: .*\[arg-type\]", mypy_output), mypy_output


def test_the_stream_protocol_is_public(mypy_output: str) -> None:
    # A wrapper annotates its stream with the protocol, imported from the package.
    errors = re.findall(r"snippet\.py:(\d+): error:", mypy_output)
    assert [line for line in errors if 29 <= int(line) <= 31] == [], mypy_output


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return match.group(1).replace("builtins.", "")
