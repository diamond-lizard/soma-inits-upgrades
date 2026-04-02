#!/usr/bin/env python3
"""Tests for build_candidate_pool merging and deduplication."""

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


def test_same_stem_prefers_pkg_el(tmp_path: Path) -> None:
    """(a) Both -pkg.el and header for same stem: pkg_el wins."""
    pkg = _write_pkg(tmp_path, "dash", 'emacs "26.1"')
    hdr = _write_header(tmp_path, "dash", 'emacs "25.1"')
    pool = build_candidate_pool([pkg], [hdr])
    assert len(pool) == 1
    assert pool[0].source_type == "pkg_el"


def test_unparseable_pkg_el_falls_back_to_header(tmp_path: Path) -> None:
    """(b) Unparseable -pkg.el with valid header: header wins."""
    bad = tmp_path / "dash-pkg.el"
    bad.write_text('(define-package "dash")', encoding="utf-8")
    hdr = _write_header(tmp_path, "dash", 'emacs "25.1"')
    pool = build_candidate_pool([bad], [hdr])
    assert len(pool) == 1
    assert pool[0].source_type == "header"


def test_different_stems_both_kept(tmp_path: Path) -> None:
    """(c) -pkg.el and header with different stems: two candidates."""
    pkg = _write_pkg(tmp_path, "dash", 'emacs "26.1"')
    hdr = _write_header(tmp_path, "magit", 'emacs "25.1"')
    pool = build_candidate_pool([pkg], [hdr])
    assert len(pool) == 2
    assert {c.stem for c in pool} == {"dash", "magit"}


def test_multiple_headers_only(tmp_path: Path) -> None:
    """(d) Multiple headers only: all appear as candidates."""
    h1 = _write_header(tmp_path, "aaa", 'emacs "25.1"')
    h2 = _write_header(tmp_path, "bbb", 'emacs "26.1"')
    pool = build_candidate_pool([], [h1, h2])
    assert len(pool) == 2

