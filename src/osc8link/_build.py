"""Build OSC 8 hyperlinks that a terminal cannot misread."""

from __future__ import annotations

import re
from typing import Literal, TextIO
from urllib.parse import quote

from ._detect import supports_hyperlinks
from ._errors import LinkError, exact, quote_short

Terminator = Literal["st", "bel"]

_TERMINATORS: dict[str, str] = {"st": "\x1b\\", "bel": "\x07"}
# The spec allows only bytes 32 to 126 in the URI and asks for URI-encoding of the rest.
# Space is encoded too, because a URI never holds a raw space; `%` stays so that an already
# encoded URI keeps its escapes.
_URL_SAFE = "".join(chr(code) for code in range(0x21, 0x7F))
# Control strings (OSC, DCS, SOS, PM, APC) in C0 or C1 form. Inside link text one would
# retarget the link or swallow its closing sequence; colours and other functions are fine.
# A terminal executes C0 controls and ignores DEL between ESC and the final byte, so
# "ESC BEL ]" still opens an OSC.
_CONTROL_STRING = re.compile(r"\x1b[\x00-\x17\x19\x1c-\x1f\x7f]*[\]PX^_]|[\x90\x98\x9d\x9e\x9f]")
_PLACEHOLDER = re.compile(r"\{(text|url)\}")


def link(url: str, text: str, *, id: str | None = None, terminator: Terminator = "st") -> str:
    """Wrap text in an OSC 8 hyperlink to url.

    Characters outside `!` to `~` in url are percent-encoded as UTF-8 (existing `%XX`
    escapes are kept). `id` joins separate pieces of text into one link on hover; an empty
    id is the same as none. The sequence ends with `ESC \\` by default or with BEL when
    terminator is "bel".

    Raises LinkError (a ValueError) for an empty url, a url holding a lone surrogate, an id
    holding `:`, `;` or a character outside 32 to 126, text holding a control string, or an
    unknown terminator; TypeError for an argument that is not a str. A str subclass is
    read by its characters alone; its own __str__ or __format__ is never called.

    >>> link("https://example.com", "Example")
    '\\x1b]8;;https://example.com\\x1b\\\\Example\\x1b]8;;\\x1b\\\\'
    >>> link("https://example.com/a b", "x", id="ref-1", terminator="bel")
    '\\x1b]8;id=ref-1;https://example.com/a%20b\\x07x\\x1b]8;;\\x07'
    """
    target, text, params, end = _parts(url, text, id, terminator)
    return f"\x1b]8;{params};{target}{end}{text}\x1b]8;;{end}"


def auto_link(
    url: str,
    text: str,
    *,
    stream: TextIO | None = None,
    fallback: str = "{text} ({url})",
    id: str | None = None,
    terminator: Terminator = "st",
) -> str:
    """Return `link(url, text)` when stream shows hyperlinks, a plain fallback otherwise.

    stream defaults to sys.stdout and is checked with `supports_hyperlinks`. The fallback
    is a template where `{text}` and `{url}` (the encoded url) are replaced and nothing else
    is interpreted; when text is the url itself the fallback is just the text. The
    arguments are checked the same way in both cases, so a bad input fails whatever the
    terminal, with the errors of `link`.

    >>> import io
    >>> auto_link("https://example.com", "docs", stream=io.StringIO())
    'docs (https://example.com)'
    >>> auto_link("https://example.com", "docs", stream=io.StringIO(), fallback="{text}")
    'docs'
    """
    target, text, params, end = _parts(url, text, id, terminator)
    fallback = exact("fallback", fallback)
    if supports_hyperlinks(stream):
        return f"\x1b]8;{params};{target}{end}{text}\x1b]8;;{end}"
    if text in (exact("url", url), target):
        return text
    values = {"text": text, "url": target}
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], fallback)


def encode_url(url: str) -> str:
    """Return url with every character outside `!` to `~` percent-encoded as UTF-8.

    Existing `%XX` escapes are kept, so encoding twice changes nothing. Raises LinkError for
    a lone surrogate, which has no UTF-8 form, and TypeError for a url that is not a str.

    >>> encode_url("https://en.wikipedia.org/wiki/\\u00c1 b")
    'https://en.wikipedia.org/wiki/%C3%81%20b'
    >>> encode_url("file:///tmp/%25x")
    'file:///tmp/%25x'
    """
    url = exact("url", url)
    try:
        return quote(url, safe=_URL_SAFE)
    except UnicodeEncodeError:
        raise LinkError("url holds a lone surrogate, which has no UTF-8 encoding") from None


def _parts(url: str, text: str, id: str | None, terminator: str) -> tuple[str, str, str, str]:
    """Check the arguments; return the encoded url, the text, the parameters and the end."""
    target = encode_url(url)
    if not target:
        raise LinkError("url must not be empty: an OSC 8 sequence without one closes a link")
    text = exact("text", text)
    if _CONTROL_STRING.search(text):
        raise LinkError("text must not hold a control string such as an OSC 8 sequence")
    terminator = exact("terminator", terminator)
    if terminator not in _TERMINATORS:
        raise LinkError(f"terminator must be 'st' or 'bel', not {quote_short(terminator)}")
    return target, text, _id_param(id), _TERMINATORS[terminator]


def _id_param(id: str | None) -> str:
    if id is None:
        return ""
    id = exact("id", id)
    if any(not 0x20 <= ord(char) <= 0x7E or char in ":;" for char in id):
        raise LinkError("id must hold only characters 32 to 126 other than ':' and ';'")
    return f"id={id}" if id else ""
