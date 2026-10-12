"""The pieces behind the line-by-line `strip` filter."""

from __future__ import annotations

import errno

import pytest

from osc8link import strip
from osc8link._cli import main
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
