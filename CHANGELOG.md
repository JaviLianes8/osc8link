# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-24

First stable release. The public API is the ten names in `osc8link.__all__` with the
signatures in the README, the `Link` fields, the `LinkError` type, the command line
(`link`, `strip`, `list`, `supports`, exit codes 0, 1 and 2) and the reading and detection
rules in the GUIDE. They change only in a new major version.

### Added

- `LinkError`, a `ValueError` subclass, raised by `link`, `auto_link` and `encode_url` for
  arguments they cannot write safely. Code that catches `ValueError` keeps working.
- `osc8link --version`.
- A GUIDE with the reading rules, the detection rules, the command line, the errors and
  the differences from VTE, xterm.js and `supports-hyperlinks`.
- Every public name documents a runnable example; the examples run as tests.

### Changed

- `strip`, `contains_link` and `iter_links` take their text as a positional-only
  argument (`strip(s=...)` no longer works) and raise `TypeError` naming the argument for
  anything but a `str`. `iter_links` raises at the call, not at the first item.
- A `terminator` or `fallback` that is not a `str` raises `TypeError` (a non-string
  terminator raised `ValueError` before). Error messages quote at most 40 characters of
  the caller's value.
- DEL inside an OSC 8 sequence is ignored, as VTE ignores it: `ESC ] 8 ; ; http://a DEL b
  ESC \` now reads as `http://ab` (0.2.0 kept the DEL in the URL).
- Detection reads numbers in the environment exactly like JavaScript's `parseInt`, as
  `supports-hyperlinks` does: leading Unicode white space such as U+00A0 or U+FEFF is
  skipped and only ASCII digits count. `FORCE_HYPERLINK=" 0"` with a no-break space and a
  `VTE_VERSION` or WezTerm date written in non-ASCII digits gave the opposite answer in
  0.2.0. `FORCE_COLOR` turns detection off when its leading number is 0 (`00`, ` 0`), not
  only for the exact text `0`.
- C0 controls and DEL inside the command number (`ESC ] 8 SOH ; ; URI`, `ESC ] 0 LF 8`) are
  ignored, as VTE and xterm.js ignore them: such a sequence is a link, which 0.2.0 missed
  (and left whole in the output of `strip`).
- `strip` leaves a CAN (U+0018) where a removed sequence had cut short an unfinished escape
  sequence or control string (`ESC [ 1`, a lone ESC, `ESC P`), so the text after it cannot
  complete that escape: the result never draws a link and stripping it again changes
  nothing. 0.2.0 could build a new link out of the text on both sides.
- `osc8link strip` holds back an opener split over two lines (`ESC`, line break, `]8;;`) and
  holds an open sequence in linear time (0.2.0 rescanned it for every line, which was
  quadratic); within the 65,536-character hold limit it gives exactly what `strip` gives on
  the whole input.
- `osc8link list` escapes bytes that are not UTF-8 as `\xNN` (0.2.0 wrote them raw,
  including the 8-bit C1 controls 0x80 to 0x9F).
- `osc8link link`, `strip` and `list` started without the stdin or stdout they need print a
  one-line message and exit 2 (0.2.0 ended with a traceback and exit code 1).
- A `str` subclass passed to any function is read by its characters alone: its own
  `__str__`, `__format__` or `__iter__` is never called, so a `(str, Enum)` member is
  written as its value and the checked text is the written text.
- `supports_hyperlinks` treats an environment value that is not a `str` as unset, says no
  for a stream whose `isatty` raises anything, and raises `TypeError` for a `platform` that
  is not a `str` (0.2.0 raised from inside `re` or returned an answer).
- `Link` and `LinkError` report `osc8link` as their module, so pickles and tracebacks name
  the public module rather than a private one.

### Removed

- The stray `osc8link.annotations` attribute.


## [0.2.0] - 2026-10-13

### Added

- `auto_link` returns the link where the terminal shows hyperlinks and `text (url)` (or a
  format of your choice) elsewhere.
- `supports_hyperlinks` guesses from the environment whether a stream shows hyperlinks:
  `FORCE_HYPERLINK`, TTY, Windows Terminal, iTerm2, WezTerm, VS Code, Ghostty, VTE,
  Alacritty, kitty, foot and more.
- `encode_url` percent-encodes everything outside printable ASCII as UTF-8.
- `link(..., terminator="bel")` writes XTerm's BEL terminator.
- `Link.id` and `Link.params` expose the parameters of a found link.
- The `osc8link` command (`link`, `strip`, `list`, `supports`), also as `python -m osc8link`.

### Changed

- `link` percent-encodes the URL, so control characters can no longer end the sequence
  early and non-ASCII URLs follow the spec. It raises `ValueError` for an empty URL, an `id`
  with `:`, `;` or a character outside 32 to 126, and text holding a control string such
  as another OSC 8 sequence. An empty `id` writes no parameter.
- `iter_links` follows the terminal state machine: an open switches the target without a
  close (0.1.0 put the second link inside the first one's text), a link left open runs to
  the end, links without visible text are skipped.
- `Link` is a frozen dataclass with `url`, `text`, `id` and `params`. It still unpacks as
  `(url, text)`, but it is no longer a tuple: it does not compare equal to one, and
  indexing (`found[0]`), `len()` and `_asdict()` are gone.
- `strip`, `contains_link` and `iter_links` read text the way the DEC parser of xterm and
  VTE does: the C1 forms of OSC and ST (`U+009D`, `U+009C`), C0 controls between ESC and
  `]`, ignored C0 controls inside the sequence, `08` as the command number, and ESC, CAN,
  SUB or a C1 control cutting a sequence short. `strip` also removes malformed, cut-short
  and unterminated OSC 8 sequences, as a terminal hides them.

## [0.1.0] - 2026-10-12

- Add `link` to build an OSC 8 hyperlink from a url and text, with an optional `id`.
- Add `strip` to remove OSC 8 sequences and keep the visible text.
- Add `contains_link` to report whether a string carries a hyperlink.
- Add `iter_links` to yield each hyperlink as a `Link(url, text)` pair.
- Accept both `ESC \` and `BEL` terminators on parse; emit `ESC \` on build.
