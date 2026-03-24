"""Tests for symbols.py (ripgrep usage search)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.symbols import (
    build_elisp_boundary_pattern,
    write_pattern_file,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_build_boundary_pattern_simple() -> None:
    """Builds a PCRE2 boundary pattern for a simple symbol."""
    pat = build_elisp_boundary_pattern("evil")
    assert "evil" in pat
    assert "(?<!" in pat
    assert "(?!" in pat


def test_build_boundary_pattern_escapes_regex() -> None:
    """Escapes regex-special characters in symbol names."""
    pat = build_elisp_boundary_pattern("foo.bar")
    assert r"foo\.bar" in pat


def test_build_boundary_pattern_hyphenated() -> None:
    """Handles hyphenated elisp symbols correctly."""
    pat = build_elisp_boundary_pattern("evil-mode")
    assert "evil\\-mode" in pat or "evil-mode" in pat


def test_write_pattern_file(tmp_path: Path) -> None:
    """Writes one pattern per line to a temp file."""
    syms = ["evil", "dash-map"]
    path = write_pattern_file(syms, tmp_path)
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert "evil" in lines[0]
    assert "dash" in lines[1]
    path.unlink()
