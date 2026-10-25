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
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t (at 1c1f914) |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links and badge tested |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-25 |
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
limit. 53 killed at once; 3 survived (M21 a cut-short tail held back, M50 Unicode digits
in a WezTerm Nix date, M55 EINVAL on a closed pipe raised) and got contracts in 056f1d6,
then were killed. The table of all 56, with the test that kills each one, is in
[CERT-1.0-MUTANTS.md](https://github.com/JaviLianes8/osc8link/blob/main/CERT-1.0-MUTANTS.md).

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Fresh clone of 1c1f914: `python -m build` and `twine check --strict` PASSED for both
  files. Wheel: the package, `py.typed`, LICENSE under `licenses/`, metadata, the console
  script. sdist: source, tests (with the oracle drivers and the manifest only), README,
  GUIDE, CHANGELOG, CONTRIBUTING, LICENSE, scripts; no fetched files, node packages,
  improvement notes or this report.
- Every interpreter on this PC from `requires-python` up, the wheel installed in a fresh
  venv and the sdist's own suite run with `src` removed (fetched sources, node oracles and
  Rich present): CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2
  free-threaded, 867 passed and 1 skipped each (the installed-wheel test, which builds
  from the source tree and runs on its own). 3.8 and 3.9 are below `requires-python`.
- `OSC8LINK_E2E=1`: the wheel and sdist are built and inspected, the wheel installed in a
  fresh venv and driven from an empty folder with `-I`: the API, `LinkError`, pickling,
  the `osc8link` script (`link`, `strip`, `--version`, exit 2) and `python -m osc8link`.

## Gates (item 15)

At 1c1f914 on this PC (CPython 3.13.2), each command on its own, with every fetched source,
the node oracles, Rich and `OSC8LINK_E2E=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (878 passed, none skipped,
doctests included) all exit 0. The library code is unchanged since 63c1848; a63c871 and
1c1f914 add only tests. Without the fetched files the tests that need them skip
cleanly, as in a fresh clone.

## QA lenses (item 19)

Five independent lenses, each reading the certification rules, running the code and
reporting only to the maintainer. Every finding, its fix and its contract are in
[CERT-1.0-QA.md](https://github.com/JaviLianes8/osc8link/blob/main/CERT-1.0-QA.md); none is disputed.

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | 3ac1c24 | FAIL | a-F1 to a-F9; fixed in 8bdf85e |
| a | 2 | d444d16 | PASS | round 1 findings confirmed fixed, no new findings |
| b. Correctness and ground truth | 1 | 3ac1c24 | FAIL | b-F1 to b-F5; fixed in 8bdf85e |
| b | 2 | d444d16 | FAIL | b-N1 (SCI before a removed sequence); fixed in 89b1a0c |
| b | 3 | 81ba3fa | PASS | no findings |
| c. Adversarial and robustness | 1 | 3ac1c24 | FAIL | c-C1 to c-C6; fixed in 8bdf85e |
| c | 2 | d444d16 | FAIL | c-N1 (hold limit counted on the whole chunk); fixed in 89b1a0c |
| c | 3 | 81ba3fa | PASS | no findings |
| d. Packaging and real e2e | 1 | 3ac1c24 | FAIL | d-D1 (closed stdin or stdout); fixed in 8bdf85e |
| d | 2 | d444d16 | FAIL | d-D2 (messages on stdout when stderr is closed); fixed in 89b1a0c |
| d | 3 | 81ba3fa | PASS | no findings |
| e. Contract strength (blind) | 1 | 3ac1c24 | FAIL | e-F1 to e-F3 and three surviving mutants; contracts in 8bdf85e |
| e | 2 | d444d16 | FAIL | e-G1 to e-G4, missing contracts on correct code; contracts in 89b1a0c |
| e | 3 | 81ba3fa | FAIL | e-H1, e-H2 (survivors M31, M07 in the let-go branch), M22 equivalent; contracts in 63c1848 |
| e | 4 | dbb91d6 | FAIL | e-F1 to e-F6 (survivors S16, D22, L14, D15, G08, E07, E08, E02), B02 equivalent; contracts in a63c871 |
| e | 5 | 0fbe619 | FAIL | round 4 findings confirmed fixed; e-N1 to e-N3 (survivors Q03, Q07, Q10 of 10 probes); contracts in 1c1f914 |
| e | 6 | | pending | |

## Independent review (item 16)

Pending.
