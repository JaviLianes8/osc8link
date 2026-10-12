"""Read every link in the VTE hyperlink test file, the test file the OSC 8 spec links to.

Source: GNOME VTE perf/hyperlink-demo.txt at commit 05d7324a8cf9cb5af32a4ced094a308139cfd34e
(URL, size and sha256 in tests/upstream/MANIFEST.json). The file is not committed: these
tests skip until `python scripts/fetch_upstream.py` has fetched it. The expected links below
were read off the file by hand and are labelled with the line they come from.
"""

from __future__ import annotations

from osc8link import Link, contains_link, iter_links, strip

EX = "http://example.com/"


def _links(demo: str) -> list[Link]:
    return list(iter_links(demo))


def test_every_link_in_the_file_is_found(vte_demo: str) -> None:
    assert len(_links(vte_demo)) == 81


def test_strip_leaves_no_osc8_sequence_and_keeps_the_rest(vte_demo: str) -> None:
    plain = strip(vte_demo)
    assert "\x1b]8" not in plain
    assert "\x9d8" not in plain
    assert not contains_link(plain)
    assert "Two adjacent links pointing to the same URL:   foofoo\n" in plain
    assert "\x1b[1mTests for gnome-terminal #779734 and iTerm2 #5158\x1b[m\n" in plain


def test_the_first_line_links_both_bug_trackers(vte_demo: str) -> None:
    first, second = _links(vte_demo)[:2]
    assert first == Link(
        "https://bugzilla.gnome.org/show_bug.cgi?id=779734", "gnome-terminal #779734"
    )
    assert second == Link("https://gitlab.com/gnachman/iterm2/issues/5158", "iTerm2 #5158")


def test_escaped_and_raw_uris_are_kept_as_written(vte_demo: str) -> None:
    urls = [found.url for found in _links(vte_demo)]
    assert "file:///var/lib/gconf/defaults/%25gconf-tree.xml" in urls
    # "Wiki page of Á (unescaped raw Latin-1; invalid UTF-8)": byte 0xC1 survives.
    assert "https://en.wikipedia.org/wiki/\udcc1" in urls
    assert "https://en.wikipedia.org/wiki/Á" in urls
    assert "https://en.wikipedia.org/wiki/%C3%81" in urls


def test_links_switched_without_a_close_are_separate(vte_demo: str) -> None:
    # "The same two without closing the first link:"
    line = next(row for row in vte_demo.splitlines() if row.startswith("The same two"))
    assert list(iter_links(line)) == [
        Link(EX + "foo", "foo"),
        Link(EX + "foo", "foo"),
        Link(EX + "foo", "foo"),
        Link(EX + "bar", "bar"),
    ]


def test_a_link_wrapping_to_the_next_line_keeps_the_break(vte_demo: str) -> None:
    # "A URL wrapping to the next line, and a trailing whitespace:"
    assert Link(EX + "foobar", "foo\nbar ") in _links(vte_demo)


def test_colour_changes_inside_a_link_stay_in_its_text(vte_demo: str) -> None:
    (colours,) = [found for found in _links(vte_demo) if found.url == EX + "colors"]
    assert colours.text.startswith("\x1b[31mM\x1b[32mu")
    assert strip(colours.text) == colours.text


def test_bel_and_c1_lines_are_read(vte_demo: str) -> None:
    found = {link.url: link.text for link in _links(vte_demo)}
    assert found[EX + "BEL"] == "BEL instead of ST"
    assert found[EX + "C1"].startswith("C1 (U+009D [UTF-8: 0xC2 0x9D] as OSC")


def test_alternating_uris_with_the_same_id(vte_demo: str) -> None:
    # "Alternating URIs, all with the same ID."
    same_id = [found for found in _links(vte_demo) if found.id == "1"]
    assert [found.url for found in same_id] == [EX + "foo", EX + "bar"] * 3 + [EX + "foo"]
    assert same_id[2].params == (("foo", "bar"), ("id", "1"))
    assert same_id[6].params == (("foo", "bar"), ("id", "1"), ("baz", "quux"))


def test_the_imaginary_editor_splits_one_link_over_two_pieces(vte_demo: str) -> None:
    editor = [found for found in _links(vte_demo) if found.id == "imaginary-text-editor-file1"]
    assert [(found.url, found.text) for found in editor] == [
        ("http://example.com", "http://exa"),
        ("http://example.com", "le.com"),
    ]


def test_long_ids_are_read_whole(vte_demo: str) -> None:
    ids = {found.id for found in _links(vte_demo) if found.url == EX + "id"}
    assert {len(found_id or "") for found_id in ids} == {250, 251}


def test_a_link_with_a_stupid_target_is_still_a_link(vte_demo: str) -> None:
    assert Link("asdfghjkl", "Explicit link with stupid target") in _links(vte_demo)
