"""The command line at its edges: a missing stderr, the hold limit, VTE's SCI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from osc8link import contains_link, strip

ROOT = Path(__file__).resolve().parents[1]
# Run the source tree when there is one, else the installed package (as from the sdist).
SRC = ROOT / "src" if (ROOT / "src").is_dir() else ROOT / "tests"


def _without_stderr(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    # Python starts with sys.stderr set to None when it has no stderr (`2>&-`, pythonw).
    code = (
        f"import sys; sys.stderr = None; from osc8link._cli import main; sys.exit(main({args!r}))"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        check=False,
        cwd=SRC,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    "args",
    [["link", ""], ["link", "https://a.test", "A", "--id", "a:b"], ["bogus"], ["link"], []],
)
def test_without_stderr_errors_exit_2_and_never_reach_stdout(args: list[str]) -> None:
    result = _without_stderr(args)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr == b""


def test_without_stderr_a_good_command_still_writes_stdout() -> None:
    result = _without_stderr(["link", "https://a.test", "A"])
    assert result.returncode == 0
    assert result.stdout.decode() == "\x1b]8;;https://a.test\x1b\\A\x1b]8;;\x1b\\\n"


def test_main_puts_a_missing_stderr_back_as_it_was(monkeypatch: pytest.MonkeyPatch) -> None:
    from osc8link._cli import main

    monkeypatch.setattr("sys.stderr", None)
    monkeypatch.setattr("sys.stdout", None)
    assert main(["link", "https://a.test"]) == 2
    assert sys.stderr is None


@pytest.mark.parametrize("args", [["list"], ["strip"], ["link", "https://a.test", "A"]])
def test_a_reader_gone_before_a_short_output_ends_the_command_quietly(args: list[str]) -> None:
    # The output is short, so it is still buffered when the write fails; without the
    # redirect to the null device, flushing it again at exit fails and Python exits 120.
    reads = args[0] != "link"
    process = subprocess.Popen(
        [sys.executable, "-m", "osc8link", *args],
        stdin=subprocess.PIPE if reads else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=SRC,
    )
    assert process.stdout is not None and process.stderr is not None
    process.stdout.close()
    if process.stdin is not None:
        process.stdin.write(b"\x1b]8;;https://a.test\x1b\\A\x1b]8;;\x1b\\\n")
        process.stdin.close()
    err = process.stderr.read()
    process.stderr.close()
    assert (process.wait(), err) == (0, b"")


def _strip(data: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "osc8link", "strip"],
        input=data.encode("utf-8", "surrogateescape"),
        capture_output=True,
        check=True,
        cwd=SRC,
    )
    return result.stdout.decode("utf-8", "surrogateescape")


@pytest.mark.parametrize(
    "data",
    [
        "\x1bZ\x1b]8;;http://x.test\x07Text\x1b]8;;\x07\n",
        "\x9a\x9d8;;http://x.test\x9cText\x9d8;;\x9c\n",
    ],
)
def test_strip_cancels_a_single_character_introducer(data: str) -> None:
    out = _strip(data)
    assert out == strip(data) == data[0] + ("Z" if data[0] == "\x1b" else "") + "\x18Text\n"


@pytest.mark.parametrize("prefix", ["\x1b\n", "\x1b\r\n", "\x1b]\n", "\x9d\n"])
def test_strip_holds_an_opener_after_a_line_past_the_limit(prefix: str) -> None:
    rest = ("]" if prefix in ("\x1b\n", "\x1b\r\n") else "") + "8;;https://evil.test\x07CLICK\n"
    data = "x" * (1 << 16) + prefix + rest
    out = _strip(data)
    assert out == strip(data)
    assert not contains_link(out)


def test_strip_cancels_an_opener_held_past_the_limit() -> None:
    data = "\x1b" + "\n" * (1 << 16) + "]8;;https://evil.test\x07CLICK\n"
    out = _strip(data)
    assert not contains_link(out)
    # Let go at 65,536 held characters, the ESC and 65,535 line breaks, then ended by a CAN.
    assert out == "\x1b" + "\n" * 65535 + "\x18\n]8;;https://evil.test\x07CLICK\n"
