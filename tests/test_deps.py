#!/usr/bin/env python3
"""Tests for deps.py (package metadata locating and parsing)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps import (
    extract_multiline_requires,
    find_package_requires_files,
    find_pkg_el_files,
    locate_package_metadata,
    parse_pkg_el,
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


def test_parse_pkg_el_with_docstring(tmp_path: Path) -> None:
    """Parse -pkg.el with DOCSTRING present."""
    pkg = tmp_path / "dash-pkg.el"
    pkg.write_text(
        '(define-package "dash" "2.19.1" "A modern list library"'
        " '((emacs \"25.1\")))",
        encoding="utf-8",
    )
    raw, name = parse_pkg_el(pkg)
    assert name == "dash"
    assert raw is not None
    assert "emacs" in raw


def test_parse_pkg_el_without_docstring(tmp_path: Path) -> None:
    """Parse -pkg.el with DOCSTRING omitted (reqs in 3rd position)."""
    pkg = tmp_path / "simple-pkg.el"
    pkg.write_text(
        "(define-package \"simple\" \"1.0\" '((emacs \"26.1\") (dash \"2.0\")))",
        encoding="utf-8",
    )
    raw, name = parse_pkg_el(pkg)
    assert name == "simple"
    assert raw is not None
    assert "dash" in raw


def test_parse_pkg_el_too_few_args(tmp_path: Path) -> None:
    """Return (None, None) for forms with fewer than 3 arguments."""
    pkg = tmp_path / "bad-pkg.el"
    pkg.write_text("(define-package \"bad\")", encoding="utf-8")
    raw, name = parse_pkg_el(pkg)
    assert raw is None
    assert name is None


def test_multiline_package_requires(tmp_path: Path) -> None:
    """Multi-line Package-Requires headers spanning 3+ lines."""
    el = tmp_path / "big.el"
    el.write_text(
        ";; Package-Requires: ((emacs \"26.1\")\n"
        ";;   (dash \"2.19.1\")\n"
        ";;   (s \"1.13.0\"))\n",
        encoding="utf-8",
    )
    lines = el.read_text(encoding="utf-8").splitlines()
    raw = extract_multiline_requires(lines, 0)
    assert "emacs" in raw
    assert "dash" in raw
    assert "s" in raw


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
