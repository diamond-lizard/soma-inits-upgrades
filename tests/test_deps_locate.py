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
    assert "26.1" in raw


def test_locate_no_metadata(tmp_path: Path) -> None:
    """locate_package_metadata returns (None, None) when nothing found."""
    raw, name = locate_package_metadata(tmp_path)
    assert raw is None
    assert name is None

def test_locate_monorepo_headers_selects_by_input(tmp_path: Path) -> None:
    """User selects a specific package from multiple header-only candidates."""
    (tmp_path / "dired-hacks-utils.el").write_text(
        ";; Package-Requires: ((emacs \"24.3\"))\n",
        encoding="utf-8",
    )
    (tmp_path / "dired-narrow.el").write_text(
        ";; Package-Requires: ((emacs \"25.1\") (dired-hacks-utils \"1.0\"))\n",
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(
        tmp_path, input_fn=lambda prompt: "2",
    )
    assert name == "dired-narrow"
    assert raw is not None
    assert "dired-hacks-utils" in raw


def test_locate_monorepo_pkg_el_selects_by_input(tmp_path: Path) -> None:
    """User selects a specific package from multiple -pkg.el candidates."""
    (tmp_path / "dash-pkg.el").write_text(
        '(define-package "dash" "2.19.1" "Lib" \'((emacs "26.1")))',
        encoding="utf-8",
    )
    (tmp_path / "s-pkg.el").write_text(
        '(define-package "s" "1.13.0" "Str" \'((emacs "24.3")))',
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(
        tmp_path, input_fn=lambda prompt: "2",
    )
    assert name == "s"
    assert raw is not None
    assert "24.3" in raw


def test_locate_mixed_monorepo_selects_by_input(tmp_path: Path) -> None:
    """Mixed monorepo: -pkg.el for one package, header for another."""
    (tmp_path / "dash-pkg.el").write_text(
        '(define-package "dash" "2.19.1" "Lib" \'((emacs "26.1")))',
        encoding="utf-8",
    )
    (tmp_path / "s.el").write_text(
        ";; Package-Requires: ((emacs \"24.3\"))\n",
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(
        tmp_path, input_fn=lambda prompt: "2",
    )
    assert name == "s"
    assert raw is not None
    assert "24.3" in raw


def test_locate_single_header_backward_compat(tmp_path: Path) -> None:
    """Single header auto-selects without extra params (backward compat)."""
    (tmp_path / "magit.el").write_text(
        ";; Package-Requires: ((emacs \"25.1\"))\n",
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(tmp_path)
    assert name == "magit"
    assert raw is not None


def test_locate_single_pkg_el_backward_compat(tmp_path: Path) -> None:
    """Single -pkg.el auto-selects without extra params (backward compat)."""
    (tmp_path / "magit-pkg.el").write_text(
        '(define-package "magit" "3.0.0" "Git" \'((emacs "25.1")))',
        encoding="utf-8",
    )
    raw, name = locate_package_metadata(tmp_path)
    assert name == "magit"
    assert raw is not None


def test_locate_empty_repo(tmp_path: Path) -> None:
    """Empty repo with no .el files returns (None, None)."""
    raw, name = locate_package_metadata(tmp_path)
    assert raw is None
    assert name is None
