"""The public surface of 1.0.0: names, signatures, docstrings and packaging promises."""

from __future__ import annotations

import dataclasses
import doctest
import importlib.resources
import inspect
import pickle
import re
import types
import typing
from pathlib import Path

import osc8link

ROOT = Path(__file__).resolve().parents[1]

# The public API. This list is the contract: the tests below fail if the module drifts.
PUBLIC_API: list[str] = [
    "Link",
    "LinkError",
    "SupportsIsatty",
    "Terminator",
    "auto_link",
    "contains_link",
    "encode_url",
    "iter_links",
    "link",
    "strip",
    "supports_hyperlinks",
]

# Signatures promised for 1.0: parameter names, kinds and defaults.
SIGNATURES: dict[str, str] = {
    "link": "(url: 'str', text: 'str', *, id: 'str | None' = None, "
    "terminator: 'Terminator' = 'st') -> 'str'",
    "auto_link": "(url: 'str', text: 'str', *, stream: 'SupportsIsatty | None' = None, "
    "fallback: 'str' = '{text} ({url})', id: 'str | None' = None, "
    "terminator: 'Terminator' = 'st') -> 'str'",
    "encode_url": "(url: 'str') -> 'str'",
    "strip": "(s: 'str', /) -> 'str'",
    "contains_link": "(s: 'str', /) -> 'bool'",
    "iter_links": "(s: 'str', /) -> 'Iterator[Link]'",
    "supports_hyperlinks": "(stream: 'SupportsIsatty | None' = None, *, "
    "env: 'Mapping[str, str] | None' = None, platform: 'str | None' = None) -> 'bool'",
    "Link": "(url: 'str', text: 'str', id: 'str | None' = None, "
    "params: 'tuple[tuple[str, str], ...]' = ()) -> None",
}


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(osc8link.__all__) == sorted(PUBLIC_API)
    assert len(set(osc8link.__all__)) == len(osc8link.__all__)


def test_every_exported_name_resolves() -> None:
    for name in osc8link.__all__:
        assert hasattr(osc8link, name)


def test_nothing_else_public_lives_on_the_package() -> None:
    public = {
        name
        for name, value in vars(osc8link).items()
        if not name.startswith("_") and not isinstance(value, types.ModuleType)
    }
    assert public == set(PUBLIC_API)


def test_every_public_function_keeps_its_signature() -> None:
    for name, expected in SIGNATURES.items():
        assert str(inspect.signature(getattr(osc8link, name))) == expected, name
        # Every annotation resolves at run time, for tools that read them.
        assert typing.get_type_hints(getattr(osc8link, name)), name


def test_the_stream_type_is_the_public_protocol() -> None:
    # A wrapper can annotate its own stream with the type the two functions declare.
    for name in ("supports_hyperlinks", "auto_link"):
        hint = typing.get_type_hints(getattr(osc8link, name))["stream"]
        assert typing.get_args(hint) == (osc8link.SupportsIsatty, type(None)), name
    assert "osc8link.SupportsIsatty" in repr(osc8link.SupportsIsatty)
    hints = typing.get_type_hints(osc8link.SupportsIsatty.isatty)
    assert hints == {"return": bool}


def test_link_fields_and_error_type_are_fixed() -> None:
    fields = [field.name for field in dataclasses.fields(osc8link.Link)]
    assert fields == ["url", "text", "id", "params"]
    assert osc8link.Link.__dataclass_params__.frozen  # type: ignore[attr-defined]
    assert issubclass(osc8link.LinkError, ValueError)
    assert osc8link.Terminator.__args__ == ("st", "bel")  # type: ignore[attr-defined]


def test_public_classes_name_the_public_module() -> None:
    # Pickles bind to __module__, so they must not name a private module that may move.
    for cls in (osc8link.Link, osc8link.LinkError, osc8link.SupportsIsatty):
        assert cls.__module__ == "osc8link"
        assert cls.__qualname__ == cls.__name__
    found = osc8link.Link("https://a.test", "A", "x", (("id", "x"),))
    data = pickle.dumps(found)
    assert b"osc8link" in data and b"_sequences" not in data
    assert pickle.loads(data) == found
    error = pickle.loads(pickle.dumps(osc8link.LinkError("bad id")))
    assert type(error) is osc8link.LinkError and str(error) == "bad id"
    assert b"_errors" not in pickle.dumps(osc8link.LinkError("bad id"))


def test_the_source_of_a_public_class_is_its_own_or_none() -> None:
    # __module__ names the package, so inspect may look in __init__.py; it must then fail
    # cleanly rather than show some other line as the class source.
    for cls in (osc8link.Link, osc8link.LinkError, osc8link.SupportsIsatty):
        try:
            source = inspect.getsource(cls)
        except OSError:
            continue
        assert source.startswith(f"class {cls.__name__}"), (cls, source[:60])


def test_every_public_name_documents_a_runnable_example() -> None:
    finder = doctest.DocTestFinder()
    for name in PUBLIC_API:
        if name == "Terminator":
            # A type alias carries no docstring of its own: the package docstring shows it.
            assert ">>>" in (osc8link.__doc__ or "")
            assert "Terminator" in (osc8link.__doc__ or "")
            continue
        value = getattr(osc8link, name)
        assert ">>>" in (value.__doc__ or ""), name
        tests = [test for test in finder.find(value, name) if test.examples]
        assert tests, name


def test_the_docstring_examples_pass() -> None:
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    for test in doctest.DocTestFinder().find(osc8link, "osc8link"):
        runner.run(test)
    for name in (name for name in PUBLIC_API if name != "Terminator"):
        for test in doctest.DocTestFinder().find(getattr(osc8link, name), name):
            runner.run(test)
    results = runner.summarize(verbose=False)
    assert results.failed == 0
    assert results.attempted >= 25


def test_version_is_a_three_part_string() -> None:
    parts = osc8link.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
    assert osc8link.__version__ == "1.0.0"


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("osc8link").joinpath("py.typed").is_file()


def test_the_package_has_no_runtime_dependency() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"^dependencies = \[\]$", text, flags=re.MULTILINE)
    assert "Development Status :: 5 - Production/Stable" in text
