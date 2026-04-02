#!/usr/bin/env python3
"""Tests for select_package_file and compute_suggested_index."""

from __future__ import annotations

from pathlib import Path

from soma_inits_upgrades.deps_selection import (
    PackageCandidate,
    compute_suggested_index,
    select_package_file,
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


def test_select_default_via_empty_input() -> None:
    """Empty input selects the suggested default."""
    cands = [_cand("aaa"), _cand("bbb"), _cand("ccc")]
    result = select_package_file(
        cands, "soma-bbb-init.el", "https://x", input_fn=lambda _: "",
    )
    assert result.stem == "bbb"


def test_select_by_number() -> None:
    """User selects a non-default option by number."""
    cands = [_cand("aaa"), _cand("bbb"), _cand("ccc")]
    result = select_package_file(
        cands, "soma-aaa-init.el", "https://x", input_fn=lambda _: "3",
    )
    assert result.stem == "ccc"


def test_invalid_then_valid_input() -> None:
    """Invalid input re-prompts, then valid input works."""
    responses = iter(["abc", "5", "2"])
    result = select_package_file(
        [_cand("aaa"), _cand("bbb"), _cand("ccc")],
        None, None, input_fn=lambda _: next(responses),
    )
    assert result.stem == "bbb"


def test_eoferror_selects_suggested() -> None:
    """EOFError falls back to suggested default."""

    def raise_eof(_: str) -> str:
        raise EOFError

    cands = [_cand("aaa"), _cand("bbb"), _cand("ccc")]
    result = select_package_file(
        cands, "soma-bbb-init.el", None, input_fn=raise_eof,
    )
    assert result.stem == "bbb"


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


def test_single_candidate_no_prompt() -> None:
    """Single candidate returns without calling input_fn."""
    called: list[str] = []

    def track_fn(prompt: str) -> str:
        called.append(prompt)
        return ""

    result = select_package_file(
        [_cand("only")], None, None, input_fn=track_fn,
    )
    assert result.stem == "only"
    assert called == []


def test_prompt_includes_context(capsys) -> None:
    """Prompt text to stderr includes repo URL and init file name."""
    select_package_file(
        [_cand("aaa"), _cand("bbb")],
        "soma-bbb-init.el", "https://github.com/ex/repo",
        input_fn=lambda _: "",
    )
    err = capsys.readouterr().err
    assert "soma-bbb-init.el" in err
    assert "https://github.com/ex/repo" in err


def test_init_file_none_defaults_to_first() -> None:
    """init_file=None defaults to first without crashing."""
    cands = [_cand("aaa"), _cand("bbb"), _cand("ccc")]
    idx = compute_suggested_index(cands, None)
    assert idx == 0
