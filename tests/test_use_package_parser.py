"""Tests for use_package_parser.py (extract_use_package_names)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.use_package_parser import extract_use_package_names

if TYPE_CHECKING:
    from pathlib import Path


def test_single_declaration(tmp_path: Path) -> None:
    """A file with a single (use-package dash) returns ["dash"]."""
    init = tmp_path / "soma-dash-init.el"
    init.write_text("(use-package dash\n", encoding="utf-8")
    assert extract_use_package_names(init) == ["dash"]


def test_three_declarations(tmp_path: Path) -> None:
    """Three declarations return names in order."""
    init = tmp_path / "soma-ivy-counsel-and-swiper-init.el"
    init.write_text(
        "(use-package ivy\n"
        "(use-package swiper\n"
        "(use-package counsel\n",
        encoding="utf-8",
    )
    assert extract_use_package_names(init) == ["ivy", "swiper", "counsel"]


def test_double_semicolon_comment_ignored(tmp_path: Path) -> None:
    """A ;;(use-package foo line (commented out) is ignored."""
    init = tmp_path / "init.el"
    init.write_text(";;(use-package foo\n(use-package bar\n", encoding="utf-8")
    assert extract_use_package_names(init) == ["bar"]


def test_single_semicolon_comment_ignored(tmp_path: Path) -> None:
    """A ;(use-package foo line (single semicolon) is ignored."""
    init = tmp_path / "init.el"
    init.write_text(";(use-package foo\n(use-package bar\n", encoding="utf-8")
    assert extract_use_package_names(init) == ["bar"]


def test_indented_declaration(tmp_path: Path) -> None:
    """An indented (use-package xclip) inside a conditional is matched."""
    init = tmp_path / "soma-xclip-init.el"
    init.write_text(
        "(if (not (display-graphic-p))\n"
        "  (use-package xclip\n"
        '    :ensure t))\n',
        encoding="utf-8",
    )
    assert extract_use_package_names(init) == ["xclip"]


def test_non_declaration_context_ignored(tmp_path: Path) -> None:
    """use-package as keyword value or in non-declaration context is ignored."""
    init = tmp_path / "init.el"
    init.write_text(
        '  :after use-package\n"use-package example"\n(use-package real\n',
        encoding="utf-8",
    )
    assert extract_use_package_names(init) == ["real"]


def test_empty_file(tmp_path: Path) -> None:
    """An empty file returns []."""
    init = tmp_path / "empty.el"
    init.write_text("", encoding="utf-8")
    assert extract_use_package_names(init) == []


def test_no_declarations(tmp_path: Path) -> None:
    """A file with no use-package declarations returns []."""
    init = tmp_path / "init.el"
    init.write_text(";; just a comment\n(setq foo 1)\n", encoding="utf-8")
    assert extract_use_package_names(init) == []


def test_nonexistent_file(tmp_path: Path) -> None:
    """A nonexistent file path returns []."""
    assert extract_use_package_names(tmp_path / "nope.el") == []


def test_outorg_outshine(tmp_path: Path) -> None:
    """Multiple declarations (outorg, outshine) returned in order."""
    init = tmp_path / "soma-outshine-and-outorg-init.el"
    init.write_text(
        "(use-package outorg\n(use-package outshine\n",
        encoding="utf-8",
    )
    assert extract_use_package_names(init) == ["outorg", "outshine"]
