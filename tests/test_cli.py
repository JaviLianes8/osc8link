from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from osc8link import link
from osc8link._cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


def run(
    *args: str, stdin: bytes = b"", env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "osc8link", *args],
        input=stdin,
        capture_output=True,
        check=False,
        cwd=SRC,
        env=env,
    )


def test_link_prints_a_hyperlink_line() -> None:
    result = run("link", "https://a.test/\u00e9", "caf\u00e9", "--id", "x")
    assert result.returncode == 0
    assert (
        result.stdout.decode("utf-8") == link("https://a.test/\u00e9", "caf\u00e9", id="x") + "\n"
    )


def test_link_text_defaults_to_the_url_and_bel_is_an_option() -> None:
    result = run("link", "https://a.test", "--bel")
    assert (
        result.stdout == link("https://a.test", "https://a.test", terminator="bel").encode() + b"\n"
    )


def test_bad_input_exits_2_with_a_message() -> None:
    result = run("link", "https://a.test", "A", "--id", "a:b")
    assert (result.returncode, result.stdout) == (2, b"")
    assert result.stderr.decode().startswith("osc8link: id must hold only")


def test_strip_round_trips_every_other_byte() -> None:
    data = b"\xef\xbb\xbfraw \xc1 byte " + link("https://a.test", "A").encode() + b"\r\nend"
    result = run("strip", stdin=data)
    assert (result.returncode, result.stdout) == (0, b"\xef\xbb\xbfraw \xc1 byte A\r\nend")


def test_list_prints_url_and_flat_text() -> None:
    data = (link("https://a.test", "two\nlines\tand tab") + link("https://b.test", "B")).encode()
    result = run("list", stdin=data)
    assert result.stdout == b"https://a.test\ttwo\\nlines\\tand tab\nhttps://b.test\tB\n"


@pytest.mark.parametrize(("force", "code"), [("1", 0), ("0", 1)])
def test_supports_reports_through_the_exit_code(force: str, code: int) -> None:
    env = {"FORCE_HYPERLINK": force, "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "PATH": ""}
    assert run("supports", env=env).returncode == code


def test_a_pipe_is_not_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORCE_HYPERLINK", raising=False)
    assert run("supports").returncode == 1


def test_a_missing_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main([])
    assert raised.value.code == 2
    assert "usage: osc8link" in capsys.readouterr().err


def test_list_escapes_controls_in_both_fields() -> None:
    # Tabs inside the payload are ignored by terminals; DEL is kept and must be escaped.
    data = ("\x1b]8;;a\x7fb\tc\x1b\\" + "\x1b[31mX\\\x1b]8;;\x1b\\").encode()
    assert run("list", stdin=data).stdout == b"a\\x7fbc\t\\x1b[31mX\\\\\n"


def test_strip_streams_line_by_line_and_holds_an_open_sequence() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "osc8link", "strip"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=SRC,
    )
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(link("https://a.test", "A").encode() + b" one\n")
    process.stdin.flush()
    assert process.stdout.readline() == b"A one\n"
    process.stdin.write(b"\x1b]8;id=\n")
    process.stdin.write(b"x;https://b.test\x1b\\B\x1b]8;;\x1b\\ two\n")
    process.stdin.close()
    assert process.stdout.read() == b"B two\n"
    assert process.wait() == 0


def test_a_reader_that_goes_away_ends_the_command_quietly() -> None:
    data = link("https://a.test", "A").encode() * 200_000
    process = subprocess.Popen(
        [sys.executable, "-m", "osc8link", "list"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=SRC,
    )
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(data)
    process.stdin.close()
    assert process.stdout.readline() == b"https://a.test\tA\n"
    process.stdout.close()
    assert process.stderr is not None
    err = process.stderr.read()
    assert (process.wait(), err) == (0, b"")


def test_help_names_the_arguments_in_capitals(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["link", "--help"])
    assert "URL [TEXT]" in capsys.readouterr().out


def test_importing_the_main_module_runs_nothing() -> None:
    import osc8link.__main__  # noqa: F401
