"""Read the links a real producer writes: Rich, run in this test when it is installed.

Rich (https://github.com/Textualize/rich) writes OSC 8 for `[link=...]` markup. Its output is
generated live, so these tests check this library against what Rich prints, not against
bytes written down by hand. They skip when Rich is not installed.
"""

from __future__ import annotations

import io
import re

import pytest

from osc8link import contains_link, iter_links, link, strip

rich_console = pytest.importorskip("rich.console")

SGR = re.compile(r"\x1b\[[0-9;]*m")


def _render(markup: str) -> str:
    out = io.StringIO()
    console = rich_console.Console(
        file=out, force_terminal=True, color_system="truecolor", width=500, legacy_windows=False
    )
    console.print(markup, end="")
    return out.getvalue()


def test_links_rich_writes_are_read_with_their_text_and_id() -> None:
    printed = _render("[link=https://a.test/x?y=1]Docs[/link] and [link=https://b.test]B[/link]")
    found = list(iter_links(printed))
    assert [(item.url, SGR.sub("", item.text)) for item in found] == [
        ("https://a.test/x?y=1", "Docs"),
        ("https://b.test", "B"),
    ]
    assert all(item.id for item in found)
    assert SGR.sub("", strip(printed)) == "Docs and B"


def test_styled_and_split_links_from_rich() -> None:
    printed = _render("[bold red][link=https://c.test]bold [green]and green[/green][/link][/]")
    assert {item.url for item in iter_links(printed)} == {"https://c.test"}
    text = "".join(SGR.sub("", item.text) for item in iter_links(printed))
    assert text == "bold and green"
    assert contains_link(printed)


def test_rich_and_link_agree_on_the_shape_of_a_plain_link() -> None:
    printed = _render("[link=https://d.test]D[/link]")
    (found,) = iter_links(printed)
    rebuilt = link(found.url, found.text, id=found.id)
    assert list(iter_links(rebuilt)) == [found]
