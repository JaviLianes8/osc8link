"""The error raised for arguments that would build a hyperlink a terminal could misread."""

from __future__ import annotations

# Messages quote at most this many characters of a caller's value.
_QUOTE_LIMIT = 40


class LinkError(ValueError):
    """Raised by `link`, `auto_link` and `encode_url` for arguments they cannot write safely.

    It is a ValueError, so code that catches ValueError keeps working. The message names the
    argument and never quotes more than a few characters of it. Arguments of the wrong type
    raise TypeError instead.

    >>> from osc8link import LinkError, link
    >>> try:
    ...     link("https://example.com", "A", id="a;b")
    ... except LinkError as error:
    ...     print(error)
    id must hold only characters 32 to 126 other than ':' and ';'
    >>> issubclass(LinkError, ValueError)
    True
    """


def quote_short(value: str) -> str:
    """Return repr(value), cut to a short prefix when value is long."""
    if len(value) <= _QUOTE_LIMIT:
        return repr(value)
    return f"{value[:_QUOTE_LIMIT]!r}... ({len(value)} characters)"


def type_error(name: str, value: object) -> TypeError:
    kind = type(value).__name__[:_QUOTE_LIMIT]
    return TypeError(f"{name} must be a str, not {kind}")
