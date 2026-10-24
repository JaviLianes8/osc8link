"""Build, detect and strip OSC 8 terminal hyperlinks.

`Terminator` names the two ways a sequence may end: "st" writes ESC backslash (the
default) and "bel" writes the BEL byte that XTerm also accepts.

>>> from osc8link import Terminator, link, strip
>>> end: Terminator = "bel"
>>> built = link("https://example.com", "Example", terminator=end)
>>> built.endswith("\\x07"), strip(built)
(True, 'Example')
"""

from ._build import Terminator, auto_link, encode_url, link
from ._detect import supports_hyperlinks
from ._errors import LinkError
from ._sequences import Link, contains_link, iter_links, strip

__version__ = "1.0.0"

__all__ = [
    "Link",
    "LinkError",
    "Terminator",
    "auto_link",
    "contains_link",
    "encode_url",
    "iter_links",
    "link",
    "strip",
    "supports_hyperlinks",
]
