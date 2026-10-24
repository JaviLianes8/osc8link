# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/osc8link/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `python scripts/fetch_upstream.py` once to fetch the spec, the VTE sources and test
  file, and (when node and npm are installed) the xterm.js and `supports-hyperlinks`
  packages the oracle tests compare against. None of it is committed; the tests that need
  it skip without it.
- Set `OSC8LINK_E2E=1` to also build the wheel and sdist and test the installed package.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
