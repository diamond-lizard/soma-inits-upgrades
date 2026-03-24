#!/usr/bin/env python3
"""Tests for deps_parsing.py and deps_header_parsing.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_header_parsing import extract_multiline_requires
from soma_inits_upgrades.deps_parsing import parse_pkg_el

if TYPE_CHECKING:
    from pathlib import Path


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
