# osc8link improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: OSC 8 spec gist, VTE hyperlink test file, ECMA-48, adoption list
- [x] Safe builder: URL percent-encoding, `id` validation, text injection guard, BEL option
- [x] Spec parser: C0 and C1 forms, all terminators, link switching, params and `id`
- [x] Terminal detection and graceful fallback
- [ ] Typed API and contracts: pinned fixtures, README, typing, installed wheel
- [x] Command line: `osc8link link|strip|list|supports`
- [ ] Docs and packaging: README, CHANGELOG, docstrings, metadata
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Mutation run: removing guarded logic makes the suite fail
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `link`, `strip`, `contains_link` and `iter_links`. Compared with the sources
below:

- `link` writes the URL and the text unchanged. A URL holding `ESC`, `BEL` or a newline
  ends the sequence early and the rest is printed or interpreted by the terminal; a URL with
  non-ASCII characters (`https://en.wikipedia.org/wiki/Á`) breaks the rule that the URI
  carries only bytes 32 to 126, URI-encoded otherwise. Text holding its own OSC 8 sequence
  silently retargets the link.
- `link(..., id="a:b")` or `id="x;y"` writes a sequence other terminals read differently,
  and `link("", "x")` writes a close, not a link.
- `iter_links` misreads the spec's state machine: a link switched to another target without
  a close (legal per the spec, used in the VTE test file) swallows the second sequence into
  the first link's text.
- Parameters other than `id` (`foo=bar:id=1`, in the VTE test file) are not exposed; the
  `id` is not exposed at all.
- C1 forms (`U+009D` as OSC, `U+009C` as ST) are not recognised, so `strip` leaves them in.
- There is no way to know whether the terminal shows links, and no fallback to print
  `text (url)` where it does not.

## Sources (fetched 2026-10-12)

- The OSC 8 specification, "Hyperlinks (a.k.a. HTML-like anchors) in terminal emulators" by
  Egmont Koblinger, gist revision 5965d6de1b609d8be0ff57b5ad9d4fe172500cf7,
  https://gist.githubusercontent.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda/raw/5965d6de1b609d8be0ff57b5ad9d4fe172500cf7/Hyperlinks_in_Terminal_Emulators.md,
  committed unchanged as `tests/data/egmontkob-hyperlinks.md`
  (sha256 fc706ddcaeab44f2a117aa94bd3e9bc583132ba908281b5bb62ad3f58367955f).
- The VTE hyperlink test file the spec links to, GNOME VTE `perf/hyperlink-demo.txt` at
  commit 05d7324a8cf9cb5af32a4ced094a308139cfd34e,
  https://gitlab.gnome.org/GNOME/vte/-/raw/master/perf/hyperlink-demo.txt, committed
  unchanged as `tests/data/vte-hyperlink-demo.txt`
  (sha256 bcd08a597353e80deeee2f18ec366ce9cf9d46713db70f1c500ad27f0b89932d).
- ECMA-48 5th edition (June 1991),
  https://ecma-international.org/wp-content/uploads/ECMA-48_5th_edition_june_1991.pdf
  (sha256 9577ad2514c411584b274ef7a4b3238c80aa93defbb349b18b8c78f78873f450), not committed.
  8.3.89 OSC: representation `09/13 or ESC 05/13`, command string in `00/08` to `00/13` and
  `02/00` to `07/14`, closed by ST. 8.3.143 ST: representation `09/12 or ESC 05/12`.
- OSC 8 adoption in terminal emulators, Alhadis/OSC8-Adoption commit
  2bb57119a930c23501fabdb59ea76947475296d1, https://github.com/Alhadis/OSC8-Adoption.
- The `supports-hyperlinks` detector (chalk), `index.js` at commit
  164e9f1f7f412715830db9d849275cd99b0ea135,
  https://raw.githubusercontent.com/chalk/supports-hyperlinks/main/index.js, read as the
  reference for environment detection. The detection tests are written by hand from it and
  labelled as such.

## Ranked improvements

1. **Safe builder.** Percent-encode every character outside `!` to `~` in the URL (UTF-8),
   which keeps existing `%XX` escapes and neutralises control characters. Reject an empty
   URL, an `id` with `:`, `;` or characters outside 32 to 126, and text holding an OSC
   opener (ESC `]` or `U+009D`), so untrusted text cannot retarget or break the link.
   `terminator="bel"` for consumers that need the XTerm form.
2. **Parser that follows the spec.** One scanner for every OSC 8 sequence in C0 or C1 form,
   ended by `ESC \`, `BEL` or `U+009C`. `iter_links` follows the state machine: an open
   switches the target, a close ends it, an open left at the end of the string runs to
   the end, empty runs are skipped. `Link` gains `id` and `params` and still unpacks as
   `(url, text)`.
3. **Ground truth contracts.** The spec's own `printf` example is built byte for byte; every
   link in the VTE test file is read with the right target and text, including switching,
   BEL, C1, params, raw UTF-8 and the 250-byte `id`s.
4. **Terminal detection and fallback.** `supports_hyperlinks(stream, env=..., platform=...)`
   modelled on `supports-hyperlinks`: `FORCE_HYPERLINK`, TTY, `TERM=dumb`, Windows Terminal,
   CI, iTerm2 3.1+, WezTerm, VS Code 1.72+, Ghostty, VTE 0.50.1+, Alacritty, kitty, foot.
   `auto_link` emits the link when supported and `text (url)` (configurable) otherwise.
5. **Typed API and docs.** `py.typed`, `mypy --strict` over a usage snippet, README with
   executed examples and the API table checked against `__all__`.
6. **Command line.** `osc8link link URL [TEXT]`, `osc8link strip` and `osc8link list` as
   filters over UTF-8 stdin (other bytes round-trip), `osc8link supports` as an exit code
   for shell scripts.
7. **Packaging.** Classifiers, keywords, console script, sdist without planning notes or
   third-party test files, installed-wheel end-to-end test.

## Out of scope

- Stripping escape sequences other than OSC 8 (colours, cursor moves): `strip` removes
  hyperlinks only; link text keeps its colours.
- Querying the terminal: the spec says there is no way to detect support, so detection
  reads the environment only.
- Building `file://` URIs with the host name: the spec asks for `gethostname()`, which is
  one line for the caller and impossible to test without the real host.
