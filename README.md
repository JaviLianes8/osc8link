# osc8link

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Build, detect and strip OSC 8 terminal hyperlinks. Zero dependencies, fully typed, checked
against the OSC 8 specification, VTE's own parser source, xterm.js and the
`supports-hyperlinks` package.

## The problem

OSC 8 is the escape sequence terminals show as a clickable link:
`ESC ] 8 ; params ; URI ESC \` before the text and `ESC ] 8 ; ; ESC \` after it. Writing
one by hand is easy to get subtly wrong: a URL holding a control character or a non-ASCII
letter breaks the sequence, text holding its own sequence retargets the link, and a pipe or
a terminal without support shows escape garbage. Reading links back (to strip them from a
log, or list them) means following the terminal's state machine, not a regular expression
for HTML-like anchors. `osc8link` does both jobs and nothing else.

## Install

```
pip install osc8link
```

## Usage

### Build a link

```python
from osc8link import LinkError, link

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
except LinkError as error:
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

The fallback is a template: `{text}` and `{url}` are replaced and nothing else is read.
`supports_hyperlinks(stream)` defaults to `sys.stdout`. A terminal cannot be asked, so it
reads the environment with the rules of the `supports-hyperlinks` npm package
(`FORCE_HYPERLINK`, TTY, Windows Terminal, iTerm2, WezTerm, VS Code, Ghostty, VTE,
Alacritty, kitty and more); the [GUIDE](https://github.com/JaviLianes8/osc8link/blob/main/GUIDE.md#detection)
lists every rule and the few deliberate differences.

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
switched = "\x1b]8;;https://a.test\x07A\x9d8;;https://b.test\x9cB"
print(list(iter_links(switched)) == [Link("https://a.test", "A"), Link("https://b.test", "B")])
# True
```

Text is read the way VTE, the terminal the spec was written for, reads it: C0 controls
other than CAN and SUB between ESC and `]` do not break the opener, C0 controls and DEL
inside the sequence (the `8` included) are ignored, and ESC (unless followed by a
backslash), CAN, SUB or a C1 control cut it short. A cut-short or unterminated sequence is not a link, and `strip`
removes it up to the character that cut it, as a terminal hides it. `strip` removes OSC 8
sequences only: colours and other escapes stay, also inside `Link.text`. Where a removed
sequence had cut short an unfinished escape before it, `strip` leaves a CAN (U+0018,
which terminals ignore) in its place, so the text after it cannot complete that escape:
the result never draws a link and stripping it again changes nothing.

### Command line

```
$ osc8link link https://example.com Example --id ref-1
$ some-command | osc8link strip > plain.log
$ some-command | osc8link list
https://a.test	A
$ osc8link supports && echo "links work here"
```

`link` prints one hyperlink (when TEXT is omitted it is the URL; an empty TEXT stays
empty; `--bel` switches the terminator). `strip` and `list` read UTF-8 from stdin and
`strip` passes any other byte through. `strip` works line by line, so it can follow a
growing log (`tail -f app.log | osc8link strip`). `list` shows control characters,
backslashes and bytes that are not UTF-8 escaped (`\x1b`, `\t`, `\\`, `\xff`), so its
output is safe to print and splits cleanly on tabs. `supports` answers through the exit
code: 0 yes, 1 no. Bad input, or a missing stdin or stdout that `link`, `strip` or `list`
needs, exits 2; messages go to stderr only, never into the output, even when stderr is
closed. `osc8link --version` and `python -m osc8link` work too.

## API

| Name | What it does |
|---|---|
| `link(url, text, *, id=None, terminator="st")` | Build a hyperlink |
| `auto_link(url, text, *, stream=None, fallback="{text} ({url})", id=None, terminator="st")` | `link` where the terminal shows links, plain text elsewhere |
| `supports_hyperlinks(stream=None, *, env=None, platform=None)` | Whether stream is a terminal known to show links |
| `encode_url(url)` | Percent-encode everything outside `!` to `~` as UTF-8 |
| `strip(s, /)` | Remove every OSC 8 sequence, keep the visible text |
| `contains_link(s, /)` | Whether s opens a link to a non-empty URI |
| `iter_links(s, /)` | An iterator over each `Link`, in order |
| `Link(url, text, id=None, params=())` | A found link; frozen, hashable, unpacks as `(url, text)` |
| `LinkError` | A `ValueError` for arguments that cannot be written safely |
| `Terminator` | `Literal["st", "bel"]` |
| `SupportsIsatty` | The type of `stream`: a protocol for any object whose `isatty()` returns a `bool` |

`link` and `auto_link` raise `LinkError` for an empty URL (an OSC 8 without one closes a
link), a URL holding a lone surrogate, an `id` holding `:`, `;` or a character outside 32
to 126, text holding a control string (OSC, DCS, SOS, PM or APC, in 7-bit or 8-bit form)
and an unknown terminator; `encode_url` raises it only for a lone surrogate. A `url`,
`text`, `fallback` or `terminator`, an `id` other than `None`, or the text given to `strip`,
`contains_link` or `iter_links` that is not a `str` raises `TypeError` (a `str` subclass is
read by its characters alone). Messages name the argument and quote at most 40 characters.
`supports_hyperlinks` raises `TypeError` only for an `env` that is not a `Mapping` (such
as `os.environ` or a `dict`) and a `platform` that is not a `str`; it treats an environment value that is not a `str` as unset and a stream whose
`isatty` fails as not a terminal. The `stream` of `supports_hyperlinks` and `auto_link` is
typed `SupportsIsatty | None`: any object whose `isatty()` returns a `bool` (`TextIO`,
`IO[str]`, `io.TextIOBase` or a class of your own) passes `mypy --strict`, and at run time
any other answer is read by its truth value. Import `SupportsIsatty` from `osc8link` to
annotate a stream of your own.

## Why

Python's standard library has nothing for OSC 8, and `click.style` (8.3.1) has no link
option. Rich (15.0.0) writes links for its `[link]` markup and reads them back in
`Text.from_ansi`, but only in the `ESC \` form: a link ended with BEL (XTerm's form, which
the spec says probably all terminals accept) or written with the C1 controls comes back as
visible text, and Rich is a full rendering toolkit with its own dependencies. The
`supports-hyperlinks` detector is JavaScript. `osc8link` is one small, typed,
dependency-free module that builds links a terminal cannot misread, reads them the way a
terminal does and tells whether the terminal will show them.

## Ground truth

The test suite checks the library against sources fetched and pinned by hash in
`tests/upstream/MANIFEST.json`, none of them committed:

- the [OSC 8 specification](https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda)
  by Egmont Koblinger and the [VTE hyperlink test file](https://gitlab.gnome.org/GNOME/vte/-/raw/master/perf/hyperlink-demo.txt)
  it links to (all 81 links read; VTE's length limits on URIs and ids are a documented
  difference);
- VTE's parser source: how every character up to U+00A0 behaves inside a sequence is read
  out of its state machine and compared with this library;
- xterm.js (`@xterm/headless`) run as a terminal on thousands of seeded random texts, every
  printed character carrying the same link;
- the `supports-hyperlinks` package run in node on hundreds of random environments;
- Rich's real output, when Rich is installed.

`python scripts/fetch_upstream.py` fetches the files and installs the node packages; the
tests that need them skip until then. The full list of sources and the cases where VTE and
xterm.js disagree are in the [GUIDE](https://github.com/JaviLianes8/osc8link/blob/main/GUIDE.md#ground-truth).

## Documentation

- [GUIDE](https://github.com/JaviLianes8/osc8link/blob/main/GUIDE.md): reading rules,
  detection rules, the command line, errors and the differences from other readers.
- [CHANGELOG](https://github.com/JaviLianes8/osc8link/blob/main/CHANGELOG.md): what changed
  in each release.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/osc8link/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
