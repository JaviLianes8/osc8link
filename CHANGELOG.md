# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

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
  `(url, text)`, but no longer compares equal to a plain tuple.
- `strip`, `contains_link` and `iter_links` read the C1 forms of OSC and ST (`U+009D`,
  `U+009C`); `strip` also removes malformed OSC 8 sequences.

## [0.1.0]

- Add `link` to build an OSC 8 hyperlink from a url and text, with an optional `id`.
- Add `strip` to remove OSC 8 sequences and keep the visible text.
- Add `contains_link` to report whether a string carries a hyperlink.
- Add `iter_links` to yield each hyperlink as a `Link(url, text)` pair.
- Accept both `ESC \` and `BEL` terminators on parse; emit `ESC \` on build.
