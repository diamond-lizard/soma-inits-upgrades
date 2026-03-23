#!/usr/bin/env python3
"""Tests for deps_processing.py (sexp parsing, filtering, version comparison)."""

from __future__ import annotations

from soma_inits_upgrades.deps_processing import (
    BUILTIN_PACKAGES,
    determine_package_name,
    filter_dependencies,
    parse_requirements_sexp,
    requires_newer_emacs,
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


def test_requires_newer_emacs_true() -> None:
    """Package requiring newer Emacs than user has."""
    assert requires_newer_emacs("28.1", "27.2") is True


def test_requires_newer_emacs_false() -> None:
    """Package requiring older Emacs than user has."""
    assert requires_newer_emacs("26.1", "29.1") is False


def test_requires_newer_emacs_equal() -> None:
    """Same version returns False."""
    assert requires_newer_emacs("27.1", "27.1") is False


def test_requires_newer_emacs_none() -> None:
    """None min_version returns False."""
    assert requires_newer_emacs(None, "29.1") is False


def test_determine_package_name_from_metadata() -> None:
    """Metadata name is returned when available."""
    assert determine_package_name("dash", "soma-dash-init.el") == "dash"


def test_determine_package_name_from_init_file() -> None:
    """Derive from init file when no metadata."""
    assert determine_package_name(None, "soma-dash-init.el") == "dash"


def test_determine_package_name_nonstandard() -> None:
    """Non-standard init file: just strip .el suffix."""
    assert determine_package_name(None, "my-package.el") == "my-package"


def test_determine_package_name_no_el_suffix() -> None:
    """No .el suffix: return as-is."""
    assert determine_package_name(None, "oddname") == "oddname"
