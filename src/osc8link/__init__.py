"""Build, detect and strip OSC 8 terminal hyperlinks."""

from __future__ import annotations

from ._build import Terminator, auto_link, encode_url, link
from ._detect import supports_hyperlinks
from ._sequences import Link, contains_link, iter_links, strip

__version__ = "0.2.0"

__all__ = [
    "Link",
    "Terminator",
    "auto_link",
    "contains_link",
    "encode_url",
    "iter_links",
    "link",
    "strip",
    "supports_hyperlinks",
]
