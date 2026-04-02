#!/usr/bin/env python3
"""Tests for build_candidate_pool (sorting, fields, dedup)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_candidate_pool import build_candidate_pool

if TYPE_CHECKING:
    from pathlib import Path


def _write_pkg(
    d: Path, stem: str, deps: str, name: str | None = None,
) -> Path:
    """Write a parseable -pkg.el file, return its path."""
    pname = name or stem
    path = d / f"{stem}-pkg.el"
    path.write_text(
        f'(define-package "{pname}" "1.0" "doc" \'({deps}))',
        encoding="utf-8",
    )
    return path


def _write_header(d: Path, stem: str, deps: str) -> tuple[Path, int]:
    """Write an .el file with a Package-Requires: header on line 1."""
    path = d / f"{stem}.el"
    path.write_text(
        f";; Package-Requires: (({deps}))\n",
        encoding="utf-8",
    )
    return path, 1


def test_multiple_pkg_el_only(tmp_path: Path) -> None:
    """All parseable -pkg.el files appear as candidates."""
    p1 = _write_pkg(tmp_path, "aaa", 'emacs "25.1"')
    bad = tmp_path / "bbb-pkg.el"
    bad.write_text("garbage", encoding="utf-8")
    p3 = _write_pkg(tmp_path, "ccc", 'emacs "26.1"')
    pool = build_candidate_pool([p1, bad, p3], [])
    assert [c.stem for c in pool] == ["aaa", "ccc"]


def test_no_duplicates_single_source_type(tmp_path: Path) -> None:
    """No duplicates when only one source type exists."""
    h1 = _write_header(tmp_path, "pkg", 'emacs "25.1"')
    pool = build_candidate_pool([], [h1])
    assert len(pool) == 1


def test_sorted_alphabetically(tmp_path: Path) -> None:
    """Candidates are sorted alphabetically by stem."""
    p1 = _write_pkg(tmp_path, "zzz", 'emacs "25.1"')
    p2 = _write_pkg(tmp_path, "aaa", 'emacs "26.1"')
    h = _write_header(tmp_path, "mmm", 'emacs "25.1"')
    pool = build_candidate_pool([p1, p2], [h])
    assert [c.stem for c in pool] == ["aaa", "mmm", "zzz"]


def test_fields_populated_correctly(tmp_path: Path) -> None:
    """embedded_name/raw_deps populated for pkg_el, None for header."""
    pkg = _write_pkg(tmp_path, "dash", 'emacs "26.1"', name="dash")
    hdr = _write_header(tmp_path, "magit", 'emacs "25.1"')
    pool = build_candidate_pool([pkg], [hdr])
    pkg_c = next(c for c in pool if c.stem == "dash")
    hdr_c = next(c for c in pool if c.stem == "magit")
    assert pkg_c.embedded_name == "dash"
    assert pkg_c.raw_deps is not None
    assert hdr_c.embedded_name is None
    assert hdr_c.raw_deps is None


def test_same_stem_same_type_keeps_first(tmp_path: Path) -> None:
    """Two -pkg.el files with same stem: first (root-level) kept."""
    sub = tmp_path / "sub"
    sub.mkdir()
    root_pkg = _write_pkg(tmp_path, "dash", 'emacs "26.1"')
    _write_pkg(sub, "dash", 'emacs "99.0"')
    pool = build_candidate_pool([root_pkg, sub / "dash-pkg.el"], [])
    assert len(pool) == 1
    assert '26.1' in (pool[0].raw_deps or "")
