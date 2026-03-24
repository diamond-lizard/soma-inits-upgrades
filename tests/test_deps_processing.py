#!/usr/bin/env python3
"""Tests for deps_processing.py (sexp parsing, filtering, version comparison)."""

from __future__ import annotations

from soma_inits_upgrades.deps_processing import (
    BUILTIN_PACKAGES,
    filter_dependencies,
    parse_requirements_sexp,
)


def test_parse_well_formed_sexp() -> None:
    """Parse a standard Package-Requires s-expression."""
    raw = '((emacs "26.1") (dash "2.19.1") (s "1.13.0"))'
    result = parse_requirements_sexp(raw)
    assert ("emacs", "26.1") in result
    assert ("dash", "2.19.1") in result
    assert ("s", "1.13.0") in result


def test_parse_missing_version() -> None:
    """Entries without versions get empty string."""
    raw = "((emacs) (dash))"
    result = parse_requirements_sexp(raw)
    assert ("emacs", "") in result
    assert ("dash", "") in result


def test_parse_empty_list() -> None:
    """Empty list returns no pairs."""
    result = parse_requirements_sexp("()")
    assert result == []


def test_parse_malformed_sexp() -> None:
    """Totally malformed input returns empty list."""
    result = parse_requirements_sexp("not a valid sexp {{{}}")
    assert result == []


def test_filter_removes_builtins() -> None:
    """Built-in packages are filtered; emacs version extracted."""
    deps = [("emacs", "26.1"), ("cl-lib", "1.0"), ("dash", "2.19.1")]
    filtered, min_emacs = filter_dependencies(deps)
    assert filtered == ["dash"]
    assert min_emacs == "26.1"


def test_filter_no_emacs_entry() -> None:
    """When no emacs entry, min_emacs is None."""
    deps = [("dash", "2.19.1"), ("s", "1.13.0")]
    filtered, min_emacs = filter_dependencies(deps)
    assert set(filtered) == {"dash", "s"}
    assert min_emacs is None


def test_builtin_packages_complete() -> None:
    """All documented built-in packages are in the constant."""
    expected = {
        "emacs", "cl-lib", "seq", "map", "nadvice", "org",
        "jsonrpc", "eldoc", "flymake", "project", "xref", "eglot",
    }
    assert expected == BUILTIN_PACKAGES

