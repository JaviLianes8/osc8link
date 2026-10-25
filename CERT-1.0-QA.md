# osc8link 1.0.0 QA rounds

The findings of the five QA lenses of [CERT-1.0-REPORT.md](https://github.com/JaviLianes8/osc8link/blob/main/CERT-1.0-REPORT.md)
(item 19), round by round, with the fix and the contract for each one.

## Round 1 (reviewed at 3ac1c24)

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

## Round 2 (reviewed at d444d16)

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

### Disputed findings

None.

## Round 3 (reviewed at 81ba3fa)

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

### Disputed findings

None.

## Round 4 (reviewed at dbb91d6)

Lens e ran a fresh blind mutation round of 116 mutants: 107 killed, B02 (`~`
percent-encoded) equivalent, and 8 survivors on correct code. Each survivor is a missing
contract, so no behaviour changed and the CHANGELOG is unchanged. All six findings are
fixed; none is disputed.

| Finding | Fix | Contract |
| --- | --- | --- |
| e-F1 (S16) the fast path for a held sequence with payload text | contracts only | test_hold::test_holding_scans_each_character_a_bounded_number_of_times now also holds an open sequence through 20,000 payload lines (`x`), a mix of payload, ENQ and line breaks, and a U+009D opener with DEL inside the payload; the timing test also streams 30,000 payload lines |
| e-F2 (D22) `env={}` read as the process environment | contracts only | test_detect::test_an_empty_env_is_read_as_is_not_as_the_process_environment: `FORCE_HYPERLINK=1` and `WT_SESSION` set in the process environment, `env={}` says False |
| e-F3 (L14) a gone reader with short output | contracts only | test_cli_edges::test_a_reader_gone_before_a_short_output_ends_the_command_quietly: `list`, `strip` and `link` with stdout closed before the first write exit 0 with an empty stderr |
| e-F4 (D15) 3-digit packed `VTE_VERSION` | contracts only | test_oracle_detect: `502` and `999` say False, recorded and checked against the package by the node oracle |
| e-F5 (G08) an OSC number other than 0 or 8 after a held opener | contracts only | test_hold_limit::test_a_held_opener_broken_by_another_command_number_goes_out_at_once: `ESC ]` and U+009D followed by `1`, `9` and `18` go out on the line that breaks them |
| e-F6 (E07, E08, E02) the 40-character quote | contracts only | test_errors::test_messages_quote_at_most_40_characters: the exact message for a 40-character value (quoted whole) and a 41-character one (first 40 and `... (41 characters)`), for `link` and `auto_link` |

Each survivor applied alone to the fixed tree fails the new contracts: S16 the payload
scan case, D22 the empty env test, L14 all 3 commands, D15 both versions, G08 every
number tried, E07 and E08 the 41-character case, E02 the 40-character case; the unmutated
tree passes them.

Contract commit: a63c871. At that commit on this PC, with every fetched source, the node
oracles, Rich and `OSC8LINK_E2E=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (CPython 3.13.2, 866 passed,
none skipped) each exit 0.

### Disputed findings

None.

## Round 5 (reviewed at 0fbe619)

Lens e reapplied the eight round 4 survivors (all now killed) and swept the changed
functions with 10 new probes: 7 killed, 3 survivors on correct code. Each survivor is a
missing contract, so no behaviour changed and the CHANGELOG is unchanged. All three
findings are fixed; none is disputed.

| Finding | Fix | Contract |
| --- | --- | --- |
| e-N1 (Q03) the fast path for an empty held payload followed by two or more ignored controls, as CRLF input gives | contracts only | test_hold::test_holding_scans_each_character_a_bounded_number_of_times now holds `ESC ] 8` and U+009D `8` openers through `\r\n` and ENQ ACK lines; the timing test also streams 30,000 `\r\n` lines after a CRLF opener |
| e-N2 (Q07) five-digit dotless versions | contracts only | test_oracle_detect: `VTE_VERSION=00100`, iTerm.app `30100` and vscode `10072` say True, recorded and checked against the package by the node oracle |
| e-N3 (Q10) the 40-character cut of a type name | contracts only | test_errors::test_a_type_name_is_quoted_up_to_40_characters: the exact `TypeError` message of `link` and `strip` for a class whose name is 40 and 41 characters long |

Each survivor applied alone to the fixed tree fails the new contracts: Q03 the three new
scan cases and the CRLF timing case, Q07 all three recorded versions, Q10 the
41-character case; the unmutated tree passes them.

Contract commit: 1c1f914. At that commit on this PC, with every fetched source, the node
oracles, Rich and `OSC8LINK_E2E=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (CPython 3.13.2, 878 passed,
none skipped) each exit 0.

### Disputed findings

None.
