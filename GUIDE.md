# osc8link guide

The README shows the common cases. This guide gives every rule the library follows, so
you can predict what it does with any input.

## Building

`link(url, text, *, id=None, terminator="st")` writes
`ESC ] 8 ; params ; URI ST text ESC ] 8 ; ; ST`.

- The URI is `encode_url(url)`: every character outside `!` to `~` (the spec allows bytes
  32 to 126 only) is percent-encoded as UTF-8, space included. `%` is kept, so a URL that
  is already encoded keeps its escapes and encoding twice changes nothing.
- `params` is `id=<id>` when an id is given, else empty. An empty id is the same as none,
  as in the spec. An id may hold the characters 32 to 126 except `:` and `;`.
- `terminator="st"` ends both sequences with `ESC \`, `terminator="bel"` with BEL.
- Text may hold colours, line breaks and any other escape sequence, but no control string
  (OSC, DCS, SOS, PM, APC) in 7-bit or 8-bit form, also when C0 controls or DEL sit between
  ESC and the final byte, because a terminal would read it as one.

`auto_link` checks its arguments exactly like `link`, then returns the link when
`supports_hyperlinks(stream)` is true and the fallback otherwise. The fallback replaces
`{text}` and `{url}` (the encoded URL) and nothing else; when the text is the URL, it is
the text alone.

```python
import io

from osc8link import auto_link, encode_url

print(encode_url(encode_url("https://a.test/ä b")))
# https://a.test/%C3%A4%20b
print(auto_link("https://a.test/ä", "a", stream=io.StringIO(), fallback="[{text}]({url})"))
# [a](https://a.test/%C3%A4)
```

## Reading

`strip`, `contains_link` and `iter_links` read text the way VTE reads it. VTE is the
terminal the OSC 8 spec was written for, and the rules below are checked against its
parser source character by character.

| Where | Character | Effect |
|---|---|---|
| between ESC and `]` | C0 controls except CAN, SUB and ESC; DEL | ignored by the opener (executed by a terminal, so `strip` keeps them, DEL excepted) |
| between ESC and `]` | CAN, SUB | the opener is broken |
| command number | `8` with any leading zeros (`08`) | OSC 8; anything else (`80`, `18`, `8x`) is not |
| inside the sequence, the command number included | C0 controls except BEL, CAN, SUB, ESC; DEL | ignored, dropped from the number, the URI and the parameters (`ESC ] 0 LF 8 SOH ; ; URI` is OSC 8) |
| inside the sequence | BEL, `U+009C`, `ESC \` | end the sequence |
| inside the sequence | ESC not followed by `\`, CAN, SUB, other C1 controls | cut the sequence short |
| inside the sequence | `U+009D` | cuts it short and starts a new one |
| inside the sequence | anything else, including non-ASCII | part of the payload |

A sequence that is cut short or reaches the end of the text is not a link; `strip` removes
it up to the character that cut it, as a terminal hides it. The ESC or C1 control that
opens an OSC 8 sequence also ends any escape sequence or control string still unfinished
before it (`ESC [ 1`, a CSI holding a BEL, a lone ESC, `ESC P ...`, an APC, SOS or PM
string, an OSC without its terminator, or VTE's single character introducer `ESC Z` or
`U+009A`, which takes the next character whatever it is). Removing
the sequence would let that earlier one run on into the text after it, so `strip` leaves a
CAN (U+0018) in its place: CAN ends any escape and a terminal shows nothing for it. When
nothing is unfinished there, nothing is added. So `strip` keeps the visible text, never
returns text that draws a link, and stripping its result again changes nothing.

A complete sequence needs two `;`: the parameters come before the second and the URI after
it (the URI may hold more `;`). A sequence without the second `;` is ignored.

`iter_links` follows the state machine of the spec: a sequence with a URI starts a link and
ends any open one, a sequence with an empty URI ends it (whatever its parameters, as in
VTE), and a link still open at the end of the text runs to the end. Links without text
are skipped. `Link.url` is the URI as written, `Link.params` every `key=value` pair in
order (pairs without `=` are dropped), and `Link.id` the first `id` value, None when it is
missing or empty. `Link.text` is the raw text between the sequences, other escapes
included. `contains_link` is true when any sequence opens a link to a non-empty URI.

```python
from osc8link import contains_link, iter_links, strip

text = "\x1b\x00]8;foo=1:id=a;http://a.\x7fb\x07A\x18\x1b]8;;\x1b\\B"
print([(item.url, item.text, item.id) for item in iter_links(text)])
# [('http://a.b', 'A\x18', 'a')]
print(repr(strip(text)), contains_link("\x1b]8;;\x1b\\"))
# '\x00A\x18B' False
```

## Detection

`supports_hyperlinks(stream=None, *, env=None, platform=None)` follows the rules of the
`supports-hyperlinks` npm package (version 4.6.0), in order:

1. A non-empty `FORCE_HYPERLINK` decides alone: false when its leading number is 0,
   true otherwise.
2. `FORCE_COLOR` set to `false`, or to a value whose leading number is 0, says no;
   `TERM=dumb` says no.
3. A stream that is not a TTY (or whose `isatty` raises an exception, any `Exception`
   subclass) says no. The stream is typed `osc8link.SupportsIsatty`, any object whose
   `isatty()` returns a `bool`; at run time any other answer is read by its truth value.
4. `WT_SESSION` (Windows Terminal) says yes, even under CI; any other Windows says no;
   `CI` or `TEAMCITY_VERSION` says no.
5. `TERM_PROGRAM`: iTerm.app 3.1 or later, WezTerm 20200620 or later (also the Nix form
   `0-unstable-2020-06-20`), vscode 1.72 or later or Cursor (`CURSOR_TRACE_ID`), ghostty,
   zed, Orca and WarpTerminal say yes; the first three (iTerm.app, WezTerm, vscode) say no
   below those versions.
6. A non-empty `VTE_VERSION` says yes when its version is 0.50 or later, written packed
   (`5001`, `7600`) or dotted (`0.50.1`), except the exact values `5000` and `0.50.0`:
   0.50.0 crashes on some links and VTE writes it as `5000`. Other spellings are read as
   numbers like the rest (`0.50` is 0.50 and says yes; `05000` is not the packed form and
   reads as version 5000).
7. `TERM` alacritty, xterm-kitty, foot, foot-extra, xterm-ghostty or wezterm says yes.
   Anything else says no.

Numbers are read like JavaScript's `parseInt`: leading white space (including U+00A0 and
U+FEFF) is skipped, then an optional sign and ASCII digits; huge values are capped. An
environment value that is not a `str` counts as unset.

Deliberate differences from `supports-hyperlinks`: command-line flags such as
`--no-hyperlink` are not read (a library does not own `sys.argv`), `NETLIFY` is not
special, `TERM=dumb` says no even when colour is forced, no colour level is required
beyond `FORCE_COLOR` not turning colour off (the package also says no when
`supports-color` finds no colour, for example with no `TERM`, or under `CI` even with
`WT_SESSION` set), `VTE_VERSION=5000` says no,
and the `TERM` values of foot, Ghostty and WezTerm are added from the OSC 8 adoption list.

## Command line

| Command | Does | Exit code |
|---|---|---|
| `osc8link link URL [TEXT] [--id ID] [--bel]` | print one link and a newline | 0, or 2 for bad input |
| `osc8link strip` | copy stdin to stdout without OSC 8 sequences, line by line | 0 |
| `osc8link list` | print `URL<TAB>TEXT` per link, controls, `\` and bytes that are not UTF-8 escaped | 0 |
| `osc8link supports` | answer whether stdout shows links | 0 yes, 1 no |
| `osc8link --version` | print the version | 0 |

`link` uses the URL as the text only when TEXT is omitted; an empty TEXT gives a link with
no visible text. Input is read as UTF-8. `strip` passes any other byte through unchanged;
`list` writes it as `\xNN`, like the controls (`\x1b`, `\x9b`), so its output holds no raw
control byte for a 7-bit or an 8-bit terminal. `strip` holds back a sequence still open at
the end of a line, or an opener not yet complete (ESC, ESC and a line break, `ESC ]`),
until the next line arrives, while the held text is shorter than 65,536 characters (not
bytes; only the held text counts, however long the line before it). When the held text
reaches 65,536 characters it is let go: an open sequence is dropped, an opener not yet
complete is written followed by a CAN, so later lines cannot complete it, and what follows
is passed on as it comes. Holding costs linear time, however long the sequence. Within that
limit, `strip` on the command line gives exactly what `strip()` gives on the whole input.
A held line goes out as soon as its sequence ends or can no longer be completed, so
`tail -f` does not stall. A reader that goes away (`osc8link list | head`) ends the
command quietly. A command started without the stdin or stdout it needs (`osc8link list
<&-`, or under `pythonw`) prints `osc8link: stdin is closed` (or `stdout`) to stderr and
exits 2. Started without stderr (`2>&-`), the commands write their messages nowhere, never
to stdout, and keep their exit codes (2 for bad input or a usage error).

## Errors

| Raised | When |
|---|---|
| `LinkError` (a `ValueError`) | empty URL (`link`, `auto_link`); URL with a lone surrogate (also `encode_url`); id with `:`, `;` or a character outside 32 to 126; text with a control string; unknown terminator |
| `TypeError` | any argument of `link`, `auto_link`, `encode_url`, `strip`, `contains_link` or `iter_links` that is not a `str`; a `platform` of `supports_hyperlinks` that is not a `str` |

Messages name the argument and quote at most 40 characters of it. A `str` subclass is
accepted and read by its characters alone: its own `__str__`, `__format__` or `__iter__`
is never called, so a `(str, Enum)` member is written as its value. `supports_hyperlinks`
never raises for odd environment values (one that is not a `str` counts as unset) or for a
stream whose `isatty` fails.

## Ground truth

`tests/upstream/MANIFEST.json` pins every source by URL, revision and hash; nothing is
committed. Fetched and checked on 2026-10-24:

- [Hyperlinks in terminal emulators](https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda),
  gist revision 5965d6de1b60: the quick example is built byte for byte, the syntax, the
  parameter example, the C1 bytes and the URI range are read from the text.
- [VTE hyperlink test file](https://gitlab.gnome.org/GNOME/vte/-/raw/05d7324a8cf9cb5af32a4ced094a308139cfd34e/perf/hyperlink-demo.txt):
  the library reads 81 links, each with the target and text the file gives it. VTE itself
  draws 78 link runs there, because its length limits (see below) apply to the lines that
  test them.
- VTE [src/parser.hh](https://gitlab.gnome.org/GNOME/vte/-/raw/5d75dcfd27bc2bfd17b1f6fddd6494abdc0355fc/src/parser.hh)
  and [src/vteseq.cc](https://gitlab.gnome.org/GNOME/vte/-/raw/5d75dcfd27bc2bfd17b1f6fddd6494abdc0355fc/src/vteseq.cc):
  the reading table above is derived from the case labels of its state machine for every
  character up to U+00A0, and the OSC 8 handler confirms the close on an empty URI.
- xterm.js, `@xterm/headless` 6.0.0, run as a terminal: 2,000 seeded random texts, every
  printed character carries the same link as `iter_links` says.
- `supports-hyperlinks` 4.6.0 run in node with exact environments: of 400 seeded random
  environments, every one where the package finds colour or `FORCE_HYPERLINK` is set (more
  than 100 of each 200) gets the same answer, and every one that is not a TTY says no in
  both; a TTY where the package finds no colour is the documented colour-level difference
  and is not compared. The recorded edge cases agree.
- Rich: the links it writes are read back with their text and id.

Where the references disagree with each other, this library follows VTE, except in two
cases, where it follows xterm.js. VTE drops a sequence whose opener and terminator mix the
7-bit and 8-bit forms (`ESC ]` with `U+009C`, `U+009D` with BEL or `ESC \`), while xterm.js
and this library read it. VTE also has length limits: a URI over 2083 bytes closes the
link, an id over 250 bytes is ignored, and an OSC string over 4096 code points is dropped
whole. xterm.js and this library apply none of them (a link read here may be one VTE does
not draw), and `strip` removes such sequences all the same. xterm.js differs from VTE (and this library) in three cases: it keeps a link open after
a sequence with parameters and no URI, keeps DEL in the URI, and applies a sequence cut by
an ESC that is not followed by a backslash.

## Upgrading from 0.2.0

See the [CHANGELOG](https://github.com/JaviLianes8/osc8link/blob/main/CHANGELOG.md). Code
that catches `ValueError` for bad values keeps working, since `LinkError` is one. Two type
checks moved: a `terminator` that is not a `str` raised `ValueError` and now raises
`TypeError`, and `iter_links` with an argument that is not a `str` raised at the first
`next()` and now raises `TypeError` at the call. Calls like `strip(s=text)` must pass the
text positionally. A DEL inside a sequence no longer reaches `Link.url`, a control inside
the command number (`ESC ] 8 SOH ; ;`) no longer hides a link, and `strip` may leave a CAN
where a removed sequence had cut short an unfinished escape.
