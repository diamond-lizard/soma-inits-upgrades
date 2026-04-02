#!/usr/bin/env python3
"""Tests for compute_suggested_index."""

from __future__ import annotations

from pathlib import Path

from soma_inits_upgrades.deps_selection import (
    PackageCandidate,
    compute_suggested_index,
)


def _cand(
    stem: str, source: str = "header", embedded: str | None = None,
) -> PackageCandidate:
    """Build a PackageCandidate with minimal boilerplate."""
    return PackageCandidate(
        stem=stem, path=Path(f"{stem}.el"), source_type=source,
        header_line=1 if source == "header" else None,
        embedded_name=embedded, raw_deps=None,
    )


def test_suggestion_matches_stem() -> None:
    """Suggestion matches init-file-derived stem."""
    cands = [_cand("aaa"), _cand("dired-hacks-utils"), _cand("zzz")]
    idx = compute_suggested_index(
        cands, "soma-dired-hacks-utils-init.el",
    )
    assert idx == 1


def test_suggestion_defaults_to_first() -> None:
    """Suggestion defaults to first when no stem matches."""
    cands = [_cand("aaa"), _cand("bbb"), _cand("ccc")]
    idx = compute_suggested_index(cands, "soma-xxx-init.el")
    assert idx == 0


def test_suggestion_two_tier_embedded_name() -> None:
    """Two-tier fallback: embedded_name match when stem doesn't."""
    cands = [
        _cand("aaa"),
        _cand("bbb-pkg", source="pkg_el", embedded="dired-hacks-utils"),
        _cand("ccc"),
    ]
    idx = compute_suggested_index(
        cands, "soma-dired-hacks-utils-init.el",
    )
    assert idx == 1


def test_init_file_none_defaults_to_first() -> None:
    """init_file=None defaults to first without crashing."""
    cands = [_cand("aaa"), _cand("bbb"), _cand("ccc")]
    idx = compute_suggested_index(cands, None)
    assert idx == 0
