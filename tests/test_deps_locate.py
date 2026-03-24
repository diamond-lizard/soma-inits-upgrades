#!/usr/bin/env python3
"""Tests for locate_package_metadata in deps.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps import locate_package_metadata

if TYPE_CHECKING:
    from pathlib import Path


def test_locate_with_header(tmp_path: Path) -> None:
    """locate_package_metadata returns data from a header file."""
    el = tmp_path / "dash.el"
    el.write_text(
        ";; Package-Requires: ((emacs \"25.1\") (s \"1.0\"))\n",
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(tmp_path)
    assert name == "dash"
    assert raw is not None
    assert "emacs" in raw


def test_locate_prefers_pkg_el(tmp_path: Path) -> None:
    """locate_package_metadata prefers -pkg.el over headers."""
    el = tmp_path / "dash.el"
    el.write_text(
        ";; Package-Requires: ((emacs \"25.1\"))\n",
        encoding="utf-8",
    )
    pkg = tmp_path / "dash-pkg.el"
    pkg.write_text(
        '(define-package "dash" "2.19.1" "Lib" \'((emacs "26.1")))',
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(tmp_path)
    assert name == "dash"
    assert raw is not None


def test_locate_no_metadata(tmp_path: Path) -> None:
    """locate_package_metadata returns (None, None) when nothing found."""
    raw, name = locate_package_metadata(tmp_path)
    assert raw is None
    assert name is None
