# osc8link 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to osc8link. Nothing is on PyPI yet
(`https://pypi.org/pypi/osc8link/json` answered 404 on 2026-10-24), so there is no release
to upgrade from; every change against 0.2.0 (the `main` branch, 9b06ecf) is in the
CHANGELOG all the same.

Progress:
- [x] Branch `release/1.0.0` created from `main` (9b06ecf, 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: spec and VTE sources fetched live, xterm.js, supports-hyperlinks, Rich (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and every Python on this PC (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] PR merged and published by the maintainer (item 17)

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: ten names, signatures, parameter kinds and defaults pinned by `tests/test_contract.py`; every change in the CHANGELOG and the GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS: no other public attribute (the stray `annotations` is gone) |
| 3 | Docstrings with runnable examples, doctests | PASS: every public name, 27 doctest lines run by `--doctest-modules` and by the contract test; README (14 outputs) and GUIDE (4) examples run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, revealed types and misuse checked from a consumer snippet |
| 5 | Typed, documented, bounded errors | PASS: `LinkError` (a `ValueError`) and `TypeError` naming the argument; messages quote at most 40 characters, tested with 1 MB inputs |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: see below |
| 8 | Real e2e from the wheel | PASS: wheel in a fresh venv driven from an empty folder, console script and `python -m`; no PyPI release to upgrade from |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links and badge tested |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-24 |
| 13 | pyproject 1.0.0, Production/Stable | PASS: classifiers 3.10 to 3.14, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` (tested) |
| 14 | sdist and wheel contents | PASS: see Packaging |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #3 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: 56 author mutants, all killed (3 after new contracts) |
| 19 | Five independent QA lenses | pending |

## Baseline on 0.2.0 (before any change)

`release/1.0.0` at 9b06ecf on this PC, CPython 3.13.2: `ruff format --check .`,
`ruff check .` and `mypy --strict src tests` exit 0; `pytest` 232 passed, 1 skipped (the
installed-wheel test, which needs `OSC8LINK_E2E=1`); no doctests existed.

Defects found in 0.2.0 by the new oracles and reproduced:

- Detection read numbers unlike `supports-hyperlinks`: `FORCE_HYPERLINK` with a leading
  U+00A0, U+FEFF or U+2028 before `0` said yes (the package says no), a `VTE_VERSION` or a
  WezTerm Nix date in Arabic-Indic digits was read as a number, `FORCE_COLOR=00` did not
  turn detection off.
- DEL inside a sequence was kept in the URL; VTE's parser ignores it.
- `osc8link.annotations` was a public attribute; a non-string terminator raised
  `ValueError`; `iter_links(5)` raised only at the first `next`; a huge terminator value
  was quoted whole in the error message.
- No public docstring had a runnable example; the README linked LICENSE relatively.

## API review (item 1)

Kept: the nine names of 0.2.0 with their signatures and defaults. Added: `LinkError`,
`osc8link --version`. Changed, all in the CHANGELOG: `LinkError` instead of plain
`ValueError` (a subclass, so callers keep working); `strip`, `contains_link`,
`iter_links` take `s` positional-only and check its type at the call; `TypeError` for a
non-string `terminator` or `fallback`; bounded messages; DEL ignored inside a sequence;
detection numbers read exactly like `parseInt`. Considered and kept: the `id` parameter
name (it is the spec's word), `Link` as a frozen dataclass, `auto_link` returning the
text alone when the text is the URL.

## Ground truth (item 7)

Fetched live on 2026-10-24 by `scripts/fetch_upstream.py` into the ignored
`tests/upstream` folder; `tests/upstream/MANIFEST.json` records URL, revision, size,
sha256 (npm integrity for packages) and licence, and the tests check them before use.

- OSC 8 spec gist, revision 5965d6de1b60 (still the latest): quick example byte for byte,
  syntax, params example, C1 bytes and URI range read from the text (`tests/test_spec.py`).
- VTE `perf/hyperlink-demo.txt` at 05d7324a8cf9 (same bytes as master): all 81 links
  (`tests/test_vte_demo.py`).
- VTE `src/parser.hh` and `src/vteseq.cc` at 5d75dcfd27bc (master): the class of every
  character up to U+00A0 inside a sequence (29 ignored, 96 collected, 2 terminators, 33
  aborts, 1 restart) and between ESC and `]` is read out of the case labels of VTE's state
  machine and compared with `iter_links`; the OSC 8 handler confirms the close on an empty
  URI and the first `id=` (`tests/test_vte_parser.py`). This found the DEL rule.
- xterm.js `@xterm/headless` 6.0.0 run in node as a terminal: 2,000 seeded random texts,
  every printed character carries the link `iter_links` gives it; three shapes where
  xterm.js differs from VTE are pinned (`tests/test_oracle_xterm.py`).
- `supports-hyperlinks` 4.6.0 (with supports-color 10.2.2) run in node with exact
  environments: 400 seeded environments over four platforms plus nine recorded edge cases
  (`tests/test_oracle_detect.py`); the documented differences are pinned in
  `tests/test_detect_differences.py`. This found the four number-reading defects.
- Rich 15.0.0 output generated in the test (`tests/test_producers.py`).

Hand-written data is labelled: `tests/test_terminal_parser.py`, `tests/test_detect.py`,
`tests/test_detect_differences.py` and the reference reader in `tests/test_fuzz.py`.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: six seeds of 4,000 random texts over the parser's alphabet compared
with an independent character-by-character reader (`strip`, `iter_links`,
`contains_link`); found URLs never hold a control; 6,000 random builds read back exactly;
the line-by-line `strip` filter equals `strip` over 6,000 random texts.
`tests/test_terminal_parser.py`: six adversarial patterns of 1 MB read in linear time.
`tests/test_errors.py`: 1 MB values in every error path, odd environment values never
raise.

## Author mutation round (item 18)

56 mutants, each applied alone to a fresh clone of the pushed branch at e6eb2ce with every
fetched source and oracle present, the full suite run with `-x` and a 300 s per-test
limit. 53 killed at once; 3 survived and got contracts in 056f1d6, then were killed.

| Mutant | Killed by |
| --- | --- |
| M01 CAN no longer aborts | test_fuzz::test_the_library_reads_like_the_reference |
| M02 SUB no longer aborts | test_fuzz::test_the_library_reads_like_the_reference |
| M03 C1 9c to 9f no longer abort | test_docs::test_every_readme_example_runs_and_prints_its_comment |
| M04 CAN allowed between ESC and `]` | test_terminal_parser::test_cancel_before_the_bracket_breaks_the_opener |
| M05 DEL breaks the opener | test_oracle_xterm::test_every_printed_character_carries_the_terminals_link |
| M06 no leading zeros in the number | test_fuzz::test_the_library_reads_like_the_reference |
| M07 `8` at the end of the text not read | test_fuzz::test_the_library_reads_like_the_reference |
| M08 C1 ST not a terminator | test_docs::test_every_readme_example_runs_and_prints_its_comment |
| M09 BEL not a terminator | doctest of `osc8link` |
| M10 DEL kept in the payload | test_cli::test_list_escapes_controls_in_both_fields |
| M11 one semicolon is enough | test_fuzz::test_the_library_reads_like_the_reference |
| M12 the last semicolon splits | test_build::test_an_injected_sequence_in_the_url_stays_inside_the_target |
| M13 links without text yielded | test_fuzz::test_the_library_reads_like_the_reference |
| M14 an open link loses its tail | doctest of `iter_links` |
| M15 a close counts as a link | doctest of `contains_link` |
| M16 the last id wins | test_parse::test_the_first_id_wins_and_the_key_is_lowercase |
| M17 parameters without `=` kept | test_build::test_control_characters_in_the_url_cannot_end_the_sequence |
| M18 an empty id kept | test_build::test_control_characters_in_the_url_cannot_end_the_sequence |
| M19 `strip` keeps the opener's DEL | test_terminal_parser::test_an_opener_with_a_control_inside_is_read |
| M20 `strip` drops the opener's C0 | test_docs::test_every_guide_example_runs_and_prints_its_comment |
| M21 a cut-short tail is held back | survived; killed by test_stream::test_a_sequence_cut_short_inside_the_line_is_not_held_back |
| M22 an open tail is never held | test_cli::test_strip_streams_line_by_line_and_holds_an_open_sequence |
| M23 space kept in the URL | doctest of `encode_url` |
| M24 DEL kept in the URL | test_build::test_control_characters_in_the_url_cannot_end_the_sequence |
| M25 APC allowed in text | test_build::test_text_holding_a_control_string_is_rejected |
| M26 C1 APC allowed in text | test_build::test_text_holding_a_control_string_is_rejected |
| M27 empty URL accepted | test_auto_link::test_bad_input_fails_whatever_the_terminal |
| M28 `;` allowed in an id | doctest of `LinkError` |
| M29 DEL allowed in an id | test_build::test_an_id_outside_the_spec_alphabet_is_rejected |
| M30 an empty id written | test_build::test_an_empty_id_is_the_same_as_none |
| M31 terminators swapped | doctest of `osc8link` |
| M32 the encoded URL repeated in the fallback | test_auto_link::test_text_that_is_the_url_is_not_repeated |
| M33 `{url}` placeholder ignored | doctest of `auto_link` |
| M34 raw URL in the fallback | test_auto_link::test_a_pipe_gets_text_and_the_encoded_url |
| M35 plain `ValueError` for an empty URL | test_errors::test_bad_values_raise_link_error_with_a_short_message |
| M36 messages not cut | test_errors::test_bad_values_raise_link_error_with_a_short_message |
| M37 an empty `FORCE_HYPERLINK` forces | doctest of `auto_link` |
| M38 `FORCE_COLOR=false` ignored | test_detect::test_unknown_or_disabled_terminals_are_not |
| M39 `FORCE_COLOR` only exact `0` | test_detect_differences::test_force_color_reads_a_leading_zero_as_off |
| M40 an empty `WT_SESSION` ignored | test_detect::test_known_terminals_are_recognised |
| M41 iTerm2 3.1 rejected | test_detect::test_known_terminals_are_recognised |
| M42 VS Code 1.72 rejected | test_detect::test_known_terminals_are_recognised |
| M43 VTE 0.50.x rejected | test_detect::test_known_terminals_are_recognised |
| M44 VTE 5000 accepted | test_detect::test_unknown_or_disabled_terminals_are_not |
| M45 Unicode digits in packed versions | test_oracle_detect::test_recorded_answers_of_the_package |
| M46 U+00A0 not white space | test_oracle_detect::test_recorded_answers_of_the_package |
| M47 the sign ignored | test_detect::test_signs_and_long_zero_runs_read_like_parse_int |
| M48 foot not known | test_detect::test_known_terminals_are_recognised |
| M49 an `isatty` OSError escapes | test_detect::test_a_stream_whose_isatty_fails_is_not_a_terminal |
| M50 Unicode digits in a WezTerm Nix date | survived; killed by test_oracle_detect::test_recorded_answers_of_the_package |
| M51 backslash not escaped by `list` | test_cli::test_list_escapes_controls_in_both_fields |
| M52 `supports` exit codes swapped | test_cli::test_supports_reports_through_the_exit_code |
| M53 bad input exits 1 | test_cli::test_bad_input_exits_2_with_a_message |
| M54 `--bel` ignored | test_cli::test_link_text_defaults_to_the_url_and_bel_is_an_option |
| M55 EINVAL on a closed pipe raised | survived; killed by test_stream::test_a_reader_that_went_away_ends_the_command_quietly |
| M56 a tiny hold limit | test_fuzz::test_the_stream_filter_strips_like_strip_over_any_line_split |

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Fresh clone of b0d3e15: `python -m build` and `twine check --strict` PASSED for both
  files. Wheel: the package, `py.typed`, LICENSE under `licenses/`, metadata, the console
  script. sdist: source, tests (with the oracle drivers and the manifest only), README,
  GUIDE, CHANGELOG, CONTRIBUTING, LICENSE, scripts; no fetched files, node packages,
  improvement notes or this report.
- Every interpreter on this PC from `requires-python` up, the wheel installed in a fresh
  venv and the sdist's own suite run with `src` removed (fetched sources, node oracles and
  Rich present): CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2
  free-threaded, 540 passed and 1 skipped each (the installed-wheel test, which builds
  from the source tree and runs on its own). 3.8 and 3.9 are below `requires-python`.
- `OSC8LINK_E2E=1`: the wheel and sdist are built and inspected, the wheel installed in a
  fresh venv and driven from an empty folder with `-I`: the API, `LinkError`, pickling,
  the `osc8link` script (`link`, `strip`, `--version`, exit 2) and `python -m osc8link`.

## Gates (item 15)

At c2600d3 on this PC (CPython 3.13.2), each command on its own, with every fetched source,
the node oracles, Rich and `OSC8LINK_E2E=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (551 passed, none skipped,
doctests included) all exit 0. Without the fetched files the tests that need them skip
cleanly, as in a fresh clone.

## QA lenses (item 19)

### Round 1 (reviewed at 3ac1c24)

Five lenses (a API and docs, b correctness and ground truth, c adversarial, d packaging
and e2e, e contract strength) reported 24 findings. Every one is fixed; none is disputed.
Each behaviour finding first got a contract that failed on 3ac1c24 (155 failures in the
in-process tests, 7 in the command line tests run against the old source, and the new
stream tests that need the new helpers), then the fix. The three surviving mutants of lens
e (C09, D09, C01), a mutant that drops the CAN and one that always rescans the held tail
were each applied to a copy of the fixed tree and are killed by the new tests.

| Finding | Fix | Contract |
| --- | --- | --- |
| a-F1, c-C5 TypeError promise and odd environment values | `supports_hyperlinks` treats a non-str environment value as unset, says no for any `isatty` failure, raises `TypeError` for a non-str `platform`; README and GUIDE say exactly which functions raise | test_errors: non-string values, platform, broken isatty |
| a-F2, c-C6 raw 8-bit bytes from `list` | `list` escapes U+DC80 to U+DCFF (undecodable bytes) as `\xNN` | test_cli::test_list_escapes_bytes_that_are_not_utf8 |
| a-F3 VTE 0.50.0 spellings | documented: only the exact values `5000` and `0.50.0` say no; other spellings are read as numbers, as `supports-hyperlinks` reads them | test_detect::test_only_the_exact_spellings_of_vte_0_50_0_say_no |
| a-F4 "the first four" | GUIDE: the first three (iTerm.app, WezTerm, vscode) | test_detect: the three below their versions fall through to nothing |
| a-F5 400 environments "agree" | GUIDE states what is compared and what is not | docs only |
| a-F6 upgrade section | GUIDE lists the terminator and `iter_links` type changes and the new reading changes | docs only |
| a-F7 private module paths | `Link.__module__` and `LinkError.__module__` are `osc8link` | test_contract::test_public_classes_name_the_public_module |
| a-F8 "64 KiB" | GUIDE: 65,536 characters, not bytes | test_hold: exact output past the limit |
| a-F9 dev extras comment | requirements-dev.txt lists all seven extras | docs only |
| b-F1 controls inside the command number | C0 controls (not BEL, CAN, SUB, ESC) and DEL may sit anywhere in `0*8` and before the `;`, for both openers | test_terminal_parser (80 cases), test_vte_parser::test_controls_inside_the_command_number_follow_vte, fuzz reference |
| b-F2 VTE length limits | documented as a deliberate difference that follows xterm.js; GUIDE ground-truth paragraph corrected (81 links read, 78 runs in VTE) | test_vte_parser::test_vte_length_limits_are_a_documented_difference, test_oracle_xterm: URIs of 2084 to 100,000 characters and a 251-character id read as xterm.js reads them |
| b-F3, c-C2 opener split over lines | the stream filter also holds an unfinished opener (ESC, ESC and controls, `ESC ]`, `ESC ] 0`, U+009D) | test_hold (9 split shapes, differential test), test_cli::test_strip_holds_an_opener_split_by_a_line_break |
| b-F4, c-C1 strip joining both sides | a CAN replaces a removed sequence whose opener ended an unfinished escape or control string; `strip` is idempotent and never returns a link | test_strip_safety (exact cases, 80,000 seeded texts), fuzz reference models the parser state |
| b-F5 "CI services give False" | docstring: WT_SESSION is checked first; GUIDE notes the package's CI colour check | test_detect_differences::test_windows_terminal_wins_over_ci |
| c-C3 quadratic hold | a held tail is rescanned only when a line could change it | test_hold: characters scanned bounded by 4x the input; hostile input about as fast as plain text |
| c-C4 str subclasses | every str argument is copied with `str.__str__` after the type check and only the copy is read and written | test_build: lying `__str__`/`__format__`/`__iter__`, `(str, Enum)` |
| d-D1 closed stdin or stdout | `link`, `strip`, `list` exit 2 with `osc8link: stdout is closed` (or stdin) | test_cli::test_a_missing_standard_stream_exits_2_with_a_message (5 cases) |
| e-F1 hold limit untested | exact output past the limit and just under it, linear-time guard | test_hold |
| e-F2 WezTerm 20200620 boundary | pinned true at 20200620, false at 20200619 | test_detect |
| e-F3 explicitly empty TEXT | pinned; README and GUIDE say the default applies only when TEXT is omitted | test_cli::test_an_explicitly_empty_text_is_kept_empty |

Every behaviour change is in the CHANGELOG 1.0.0 section. Fix commit: 8bdf85e. At that
commit on this PC (CPython 3.13.2, every fetched source, the node oracles, Rich and
`OSC8LINK_E2E=1`): `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (782 passed, none skipped) each exit 0.

### Round 2 (reviewed at d444d16)

Every round 1 finding was re-checked as fixed by its lens. Lenses b, c, d and e
reported 7 new findings. Every one is fixed; none is disputed. The behaviour
findings first got contracts that fail on d444d16: 44 failures when the new and changed
test files run against the d444d16 source, then the fix.

| Finding | Fix | Contract |
| --- | --- | --- |
| b-N1 SCI before a removed sequence | `strip` treats VTE's single character introducer (`ESC Z`, controls and DEL allowed between, or U+009A, followed only by DEL) as unfinished and leaves a CAN after it, so it cannot swallow the first visible character; GUIDE and CHANGELOG list it | test_strip_safety (4 SCI cases, 5 finished SCI cases), test_cli_edges::test_strip_cancels_a_single_character_introducer (both forms by subprocess), fuzz reference models SCI |
| c-N1 hold limit counted on the whole chunk | the limit counts the held text only (`len(pending) - cut`), so a long line no longer stops a short opener from being held; held text that reaches the limit is let go with a CAN after an opener prefix, so later lines cannot complete it; GUIDE says exactly what is let go | test_hold_limit: long lines (65,533 to 131,072 characters) ending in ESC, ESC CR LF, `ESC ]`, `ESC ]` CR LF, U+009D, ESC ENQ; an opener held to exactly the limit; test_cli_edges by subprocess |
| d-D2 messages on stdout when stderr is closed | `main` replaces a missing stderr with a sink while it runs and puts None back, so neither argparse nor the error path falls back to stdout; a usage error exits 2 on 3.10 too; README, GUIDE, CHANGELOG | test_cli_edges::test_without_stderr_errors_exit_2_and_never_reach_stdout (5 cases), good command still writes stdout, stderr restored |
| e-G1 CAN guard unpinned for CSI with BEL and APC | contracts only | test_strip_safety: CSI holding BEL (7-bit and 8-bit), APC (`ESC _`, U+009F), SOS, PM; APC and SCI added to both fuzz alphabets, a CSI holding BEL to the reference fuzz |
| e-G2 exact 65,536 boundary | contracts only | test_hold_limit::test_the_hold_limit_is_exactly_65_536_characters: 65,535 held whole, 65,536 let go, through the fast path and the rescan path |
| e-G3 when held lines go out | contracts only; GUIDE says a held line goes out as soon as its sequence ends or breaks | test_hold_limit::test_a_held_line_goes_out_as_soon_as_its_sequence_ends_or_breaks (lines read before each chunk) |
| e-G4 str subclass environment values | contracts only | test_errors::test_detection_reads_a_str_subclass_value_by_its_characters |

The lens e survivors and mutants of the new code, each applied alone to a copy of the
fixed tree and run against the whole suite with `-x` (fetched sources, node oracles
present), are all killed:

| Mutant | Killed by |
| --- | --- |
| N19 BEL no longer kept inside a CSI | test_fuzz::test_the_library_reads_like_the_reference |
| N21 APC not a control string | test_fuzz::test_the_library_reads_like_the_reference |
| N08 fast path `<` to `<=` | test_cli_edges::test_strip_cancels_an_opener_held_past_the_limit |
| C09c let-go check `<` to `<=` | test_cli_edges::test_strip_cancels_an_opener_held_past_the_limit |
| N30 `KEEP_PAYLOAD` takes anything | test_hold_limit::test_a_held_line_goes_out_as_soon_as_its_sequence_ends_or_breaks |
| N31 `keep_pattern` always `KEEP_PAYLOAD` | test_hold::test_an_opener_that_cannot_be_completed_any_more_is_let_go |
| N32 a C1 tail keeps controls | test_hold_limit::test_a_held_line_goes_out_as_soon_as_its_sequence_ends_or_breaks |
| N43 environment read through the subclass | test_errors::test_detection_reads_a_str_subclass_value_by_its_characters |
| S1 SCI not unfinished | test_cli_edges::test_strip_cancels_a_single_character_introducer |
| S2 U+009A not SCI | test_cli_edges::test_strip_cancels_a_single_character_introducer |
| S3 DEL ends SCI | test_fuzz::test_the_library_reads_like_the_reference |
| S4 controls between ESC and `Z` break SCI | test_fuzz::test_the_library_reads_like_the_reference |
| S5 no CAN after an opener let go | test_cli_edges::test_strip_cancels_an_opener_held_past_the_limit |
| S6 limit counted on the whole chunk again | test_cli_edges::test_strip_holds_an_opener_after_a_line_past_the_limit |
| S7 missing stderr not replaced | test_cli_edges::test_without_stderr_errors_exit_2_and_never_reach_stdout |

Every behaviour change is in the CHANGELOG 1.0.0 section. Fix commit: 89b1a0c. At that
commit on this PC, with every fetched source, the node oracles, Rich and
`OSC8LINK_E2E=1`: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (CPython 3.13.2, 839 passed, none skipped) each
exit 0; CPython 3.10.19 runs the suite with 835 passed and 3 skipped (Rich not installed
there, and the installed-wheel test).

#### Disputed findings

None.

### Round 3 (reviewed at 81ba3fa)

Lens e re-checked every earlier finding as fixed (C01, C09, C09b, D09, G1 to G4 and their
mutants are killed) and swept 24 mutants of the code changed since d444d16: 21 killed,
M22 (SCI stand-in `ESC` instead of `ESC Z`) equivalent, as a differential fuzz of 783,938
inputs confirmed, and two survivors in the let-go branch of the stream filter. Both are
missing contracts on correct code, so no behaviour changed and the CHANGELOG is unchanged.
Both are fixed; none is disputed.

| Finding | Fix | Contract |
| --- | --- | --- |
| e-H1 let-go after an unfinished escape (M31: the let-go strips with an empty state) | contracts only | test_hold_limit::test_a_let_go_opener_cancels_the_escape_left_unfinished_before_it: `ESC [ 1`, a lone ESC, `ESC P` and U+009B `1` right before an opener held to exactly 65,536 characters; the exact output has the CAN right after the escape |
| e-H2 state not reset after a let-go (M07: the stale state is kept) | contracts only | test_hold_limit::test_after_a_let_go_the_next_line_is_stripped_as_it_comes: after an `ESC ]` number prefix in one long line, ESC and U+009D followed by line breaks up to the limit, a line holding a complete link comes out as exactly one CAN and then `strip()` of that line |

Each survivor applied alone to a copy of the fixed tree fails the new tests: M31 fails all
4 escape cases, M07 all 3 prefix cases; the unmutated tree passes them.

Fix commit: 63c1848. At that commit on this PC, with every fetched source, the node
oracles, Rich and `OSC8LINK_E2E=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (CPython 3.13.2, 846 passed,
none skipped) each exit 0.

#### Disputed findings

None.

## Independent review (item 16)

Pending.
