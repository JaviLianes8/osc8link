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
    assert result.stdout == b"https://a.test\ttwo lines and tab\nhttps://b.test\tB\n"


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
