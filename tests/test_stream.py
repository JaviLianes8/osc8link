"""The pieces behind the line-by-line `strip` filter."""

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from osc8link import strip
from osc8link._cli import _strip_stream, main
from osc8link._sequences import unfinished_tail


@pytest.mark.parametrize("opener", ["\x1b]", "\x9d"])
def test_an_open_sequence_at_the_end_is_held_back(opener: str) -> None:
    text = f"A {opener}8;;https://b.test\n"
    assert unfinished_tail(text) == 2


def test_a_finished_sequence_at_the_end_is_not_held_back() -> None:
    text = "A\x1b]8;;https://b.test\x1b\\B\x1b]8;;\x1b\\"
    assert unfinished_tail(text) == len(text)
    closed = "A\x1b]8;;\x07"
    assert unfinished_tail(closed) == len(closed)


def test_plain_text_and_other_escapes_are_not_held_back() -> None:
    assert unfinished_tail("no escapes\n") == len("no escapes\n")
    assert unfinished_tail("red \x1b[31m\n") == len("red \x1b[31m\n")


def test_a_bare_opener_at_the_end_is_hidden_and_held() -> None:
    assert strip("a\x1b]8") == "a"
    assert unfinished_tail("a\x1b]8") == 1


class _Full:
    def write(self, data: bytes) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")

    def flush(self) -> None:
        pass


class _FullStdout:
    buffer = _Full()


def test_write_errors_other_than_a_closed_pipe_are_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdout", _FullStdout())
    with pytest.raises(OSError, match="No space"):
        main(["link", "https://a.test"])


def test_a_sequence_cut_short_inside_the_line_is_not_held_back() -> None:
    line = "a\x1b]8;;x\x18b\n"
    assert unfinished_tail(line) == len(line)
    chunks = _strip_stream(iter([line, "c\n"]))
    assert next(chunks) == "a\x18b\n"


class _Gone:
    def __init__(self, code: int) -> None:
        self.code = code

    def write(self, data: bytes) -> int:
        raise OSError(self.code, "the reader went away")

    def flush(self) -> None:
        pass


@pytest.mark.parametrize("code", [errno.EINVAL, errno.EPIPE])
def test_a_reader_that_went_away_ends_the_command_quietly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, code: int
) -> None:
    with (tmp_path / "out").open("wb") as target:

        class _Stdout:
            buffer = _Gone(code)

            def fileno(self) -> int:
                return target.fileno()

        monkeypatch.setattr("sys.stdout", _Stdout())
        assert main(["link", "https://a.test"]) == 0
