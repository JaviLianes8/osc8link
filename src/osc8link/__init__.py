"""Build, detect and strip OSC 8 terminal hyperlinks."""

from __future__ import annotations

from ._osc8 import Link, contains_link, iter_links, link, strip

__version__ = "0.1.0"

__all__ = ["Link", "contains_link", "iter_links", "link", "strip"]
