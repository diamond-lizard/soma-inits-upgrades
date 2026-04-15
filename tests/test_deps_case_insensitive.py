"""Tests for case-insensitive Package-Requires: header handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_finders import find_package_requires_files
from soma_inits_upgrades.deps_header_parsing import extract_multiline_requires

if TYPE_CHECKING:
    from pathlib import Path


def test_find_package_requires_lowercase_r(tmp_path: Path) -> None:
    """Lowercase 'r' in Package-requires: is detected."""
    el = tmp_path / "dired-hacks-utils.el"
    el.write_text(
        ';; Package-requires: ((dash "2.5.0"))\n',
        encoding="utf-8",
    )
    result = find_package_requires_files(tmp_path)
    assert len(result) == 1
    assert result[0] == (el, 1)


def test_find_package_requires_all_caps(tmp_path: Path) -> None:
    """All-caps PACKAGE-REQUIRES: is detected."""
    el = tmp_path / "pkg.el"
    el.write_text(
        ';;; PACKAGE-REQUIRES: ((emacs "25.1"))\n',
        encoding="utf-8",
    )
    result = find_package_requires_files(tmp_path)
    assert len(result) == 1


def test_find_package_requires_mixed_case(tmp_path: Path) -> None:
    """Mixed case package-REQUIRES: is detected."""
    el = tmp_path / "pkg.el"
    el.write_text(
        ';; package-REQUIRES: ((emacs "26.1"))\n',
        encoding="utf-8",
    )
    result = find_package_requires_files(tmp_path)
    assert len(result) == 1


def test_extract_multiline_requires_lowercase_r(tmp_path: Path) -> None:
    """extract_multiline_requires handles lowercase Package-requires:."""
    el = tmp_path / "dired-hacks-utils.el"
    content = ';; Package-requires: ((dash "2.5.0"))\n'
    el.write_text(content, encoding="utf-8")
    lines = content.splitlines()
    result = extract_multiline_requires(lines, 0)
    assert result == '((dash "2.5.0"))'


def test_extract_multiline_requires_all_caps(tmp_path: Path) -> None:
    """extract_multiline_requires handles all-caps PACKAGE-REQUIRES:."""
    el = tmp_path / "pkg.el"
    content = ';;; PACKAGE-REQUIRES: ((emacs "25.1"))\n'
    el.write_text(content, encoding="utf-8")
    lines = content.splitlines()
    result = extract_multiline_requires(lines, 0)
    assert result == '((emacs "25.1"))'
