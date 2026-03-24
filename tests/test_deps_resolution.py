#!/usr/bin/env python3
"""Tests for deps_resolution.py (package name resolution, version comparison)."""

from __future__ import annotations

from soma_inits_upgrades.deps_resolution import (
    determine_package_name,
    requires_newer_emacs,
)


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
