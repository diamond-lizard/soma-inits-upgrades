#!/usr/bin/env python3
"""Tests for deps.py (package metadata locating and parsing)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_finders import (
    find_package_requires_files,
    find_pkg_el_files,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_find_pkg_el_at_root(tmp_path: Path) -> None:
    """Root-level -pkg.el files are found."""
    pkg = tmp_path / "dash-pkg.el"
    pkg.write_text('(define-package "dash" "2.19.1")', encoding="utf-8")
    result = find_pkg_el_files(tmp_path)
    assert result == [pkg]


def test_find_pkg_el_in_subdir(tmp_path: Path) -> None:
    """Subdirectory -pkg.el files are found."""
    lisp = tmp_path / "lisp"
    lisp.mkdir()
    pkg = lisp / "magit-pkg.el"
    pkg.write_text('(define-package "magit" "3.0.0")', encoding="utf-8")
    result = find_pkg_el_files(tmp_path)
    assert result == [pkg]


def test_find_pkg_el_root_before_subdir(tmp_path: Path) -> None:
    """Root-level files sort before subdirectory files."""
    root_pkg = tmp_path / "dash-pkg.el"
    root_pkg.write_text('(define-package "dash" "2.19.1")', encoding="utf-8")
    lisp = tmp_path / "lisp"
    lisp.mkdir()
    sub_pkg = lisp / "magit-pkg.el"
    sub_pkg.write_text('(define-package "magit" "3.0.0")', encoding="utf-8")
    result = find_pkg_el_files(tmp_path)
    assert result == [root_pkg, sub_pkg]


def test_find_package_requires_header(tmp_path: Path) -> None:
    """Package-Requires: headers are found with line numbers."""
    el = tmp_path / "dash.el"
    el.write_text(
        ";; Package-Requires: ((emacs \"25.1\"))\n;; more\n",
        encoding="utf-8",
    )
    result = find_package_requires_files(tmp_path)
    assert len(result) == 1
    assert result[0] == (el, 1)


def test_find_package_requires_triple_semicolons(tmp_path: Path) -> None:
    """Headers with three semicolons are detected."""
    el = tmp_path / "pkg.el"
    el.write_text(
        ";;; foo\n;;; Package-Requires: ((emacs \"26.1\"))\n",
        encoding="utf-8",
    )
    result = find_package_requires_files(tmp_path)
    assert len(result) == 1
    assert result[0][1] == 2

