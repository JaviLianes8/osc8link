# osc8link

Build, detect and strip OSC 8 terminal hyperlinks. Zero dependencies, fully typed, checked
against the OSC 8 specification and the VTE hyperlink test file.

## Install

```
pip install osc8link
```

## Usage

### Build a link

```python
from osc8link import link

cell = link("https://example.com", "Example")
print(repr(cell))
# '\x1b]8;;https://example.com\x1b\\Example\x1b]8;;\x1b\\'

# An id joins pieces of text (a link split over two lines) into one link on hover.
print(repr(link("https://example.com", "Exa", id="ref-1")))
# '\x1b]8;id=ref-1;https://example.com\x1b\\Exa\x1b]8;;\x1b\\'

# The URI may carry only printable ASCII, so anything else is percent-encoded as UTF-8.
# Control characters cannot end the sequence early; existing %XX escapes are kept.
print(repr(link("https://en.wikipedia.org/wiki/Á b", "A")))
# '\x1b]8;;https://en.wikipedia.org/wiki/%C3%81%20b\x1b\\A\x1b]8;;\x1b\\'

# Some programs want XTerm's BEL terminator instead of ESC backslash.
print(repr(link("https://example.com", "x", terminator="bel")))
# '\x1b]8;;https://example.com\x07x\x1b]8;;\x07'

# Text with its own control string (another OSC 8 link, say) would retarget the link.
try:
    link("https://example.com", "\x1b]8;;https://evil.test\x1b\\click")
except ValueError as error:
    print(error)
    # text must not hold a control string such as an OSC 8 sequence
```

### Print a link only where the terminal shows it

```python
import io

from osc8link import auto_link, supports_hyperlinks

pipe = io.StringIO()  # not a terminal, like `program | less`
print(supports_hyperlinks(pipe))
# False
print(auto_link("https://example.com", "docs", stream=pipe))
# docs (https://example.com)
print(auto_link("https://example.com", "docs", stream=pipe, fallback="{text} <{url}>"))
# docs <https://example.com>
print(auto_link("https://example.com", "https://example.com", stream=pipe))
# https://example.com
```

`supports_hyperlinks(stream)` defaults to `sys.stdout`. The spec says a terminal cannot be
asked, so it reads the environment, with the rules of the `supports-hyperlinks` npm
package:

- `FORCE_HYPERLINK=1` always says yes and `FORCE_HYPERLINK=0` always says no.
- Otherwise the stream must be a TTY, `TERM` must not be `dumb` and `FORCE_COLOR` must not
  be `0` or `false`; CI services (`CI`, `TEAMCITY_VERSION`) say no.
- Recognised: Windows Terminal (`WT_SESSION`), iTerm2 3.1+, WezTerm, VS Code 1.72+ and
  Cursor, Ghostty, Zed, Warp, Orca, VTE 0.50.1+ (GNOME Terminal, Tilix, Ptyxis and the
  rest), and the `TERM` of Alacritty, kitty, foot, Ghostty and WezTerm. Anything else on
  Windows says no.

### Read and strip links

```python
from osc8link import Link, contains_link, iter_links, link, strip

line = "see " + link("https://a.test", "A", id="x") + " and " + link("https://b.test", "B")
print(strip(line))
# see A and B
print(contains_link(line), contains_link("plain"))
# True False
print([(url, text) for url, text in iter_links(line)])
# [('https://a.test', 'A'), ('https://b.test', 'B')]

first = next(iter_links(line))
print(first.id, first.params)
# x (('id', 'x'),)

# Terminals are state machines: an open switches the target without a close, and a link
# left open runs to the end of the text. ESC backslash, BEL and the C1 forms are all read.
switched = "\x1b]8;;https://a.test\x07A\x1b]8;;https://b.test\x9cB"
print(list(iter_links(switched)) == [Link("https://a.test", "A"), Link("https://b.test", "B")])
# True
```

`strip` removes OSC 8 sequences only: colours and other escapes stay, also inside
`Link.text`. Only an OSC 8 sequence ends a link (a terminal reset would end one on screen
too).

### Command line

```
$ osc8link link https://example.com Example --id ref-1
$ some-command | osc8link strip > plain.log
$ some-command | osc8link list
https://a.test	A
$ osc8link supports && echo "links work here"
```

`link` prints one hyperlink (the text defaults to the URL, `--bel` switches the
terminator). `strip` and `list` read UTF-8 from stdin and pass any other byte through.
`supports` answers through the exit code: 0 yes, 1 no. Bad input exits 2.
`python -m osc8link` works too.

## API

| Name | What it does |
|---|---|
| `link(url, text, *, id=None, terminator="st")` | Build a hyperlink; raises `ValueError` on input a terminal could misread |
| `auto_link(url, text, *, stream=None, fallback="{text} ({url})", id=None, terminator="st")` | `link` where the terminal shows links, plain text elsewhere |
| `supports_hyperlinks(stream=None, *, env=None, platform=None)` | Whether stream is a terminal known to show links |
| `encode_url(url)` | Percent-encode everything outside `!` to `~` as UTF-8 |
| `strip(s)` | Remove every OSC 8 sequence, keep the visible text |
| `contains_link(s)` | Whether s opens a link to a non-empty URI |
| `iter_links(s)` | Yield each `Link` in order |
| `Link(url, text, id=None, params=())` | A found link; frozen, hashable, unpacks as `(url, text)` |
| `Terminator` | `Literal["st", "bel"]` |

`link` rejects an empty URL (an OSC 8 without one closes a link), an `id` holding `:`, `;`
or a character outside 32 to 126, and text holding a control string (OSC, DCS, SOS, PM or
APC, in 7-bit or 8-bit form). An empty `id` is the same as none, as in the spec.

## Why

OSC 8 is the escape sequence terminals render as a clickable hyperlink:
`ESC ] 8 ; params ; URI ESC \` around the text, closed by `ESC ] 8 ; ; ESC \`.
Full terminal toolkits know how to emit it, but the primitive is buried inside them, and
inline snippets copied between projects write URLs unencoded and read links as if they
were HTML anchors. This package does the one job and follows the spec.

## Sources

- [Hyperlinks in terminal emulators](https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda),
  the OSC 8 specification by Egmont Koblinger.
- [VTE hyperlink test file](https://gitlab.gnome.org/GNOME/vte/-/raw/master/perf/hyperlink-demo.txt):
  every link in it is read correctly, tested.
- [ECMA-48](https://ecma-international.org/publications-and-standards/standards/ecma-48/),
  8.3.89 (OSC) and 8.3.143 (ST).
- [OSC 8 adoption in terminal emulators](https://github.com/Alhadis/OSC8-Adoption) and
  [supports-hyperlinks](https://github.com/chalk/supports-hyperlinks) for detection.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
