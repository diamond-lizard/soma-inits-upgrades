#!/usr/bin/env python3
"""Tests for multi-repo finalization: uniform outcomes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.processing_finalize import finalize_entry
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path

URL_A = "https://github.com/test/repo-a"
URL_B = "https://github.com/test/repo-b"


def _repo(
    done_reason: str | None = None, notes: str | None = None,
    url: str = URL_A,
) -> RepoState:
    """Build a RepoState with optional done_reason and notes."""
    r = RepoState(
        repo_url=url,
        pinned_ref="abc1234567890abcdef1234567890abcdef123456",
    )
    r.done_reason = done_reason
    r.notes = notes
    return r


def _make_ctx(tmp_path: Path, repos: list[RepoState]):
    """Build an in-progress EntryContext with given repos."""
    from runner_helpers import make_ctx
    ctx = make_ctx(tmp_path, repos)
    ctx.entry_state.status = "in_progress"
    return ctx


def test_all_repos_already_latest(tmp_path: Path) -> None:
    """(a) ALL repos already_latest -> entry 'already_latest'."""
    repos = [_repo("already_latest"), _repo("already_latest", url=URL_B)]
    ctx = _make_ctx(tmp_path, repos)
    finalize_entry(ctx)
    assert ctx.entry_state.done_reason == "already_latest"
    assert ctx.entry_state.status == "done"


def test_all_repos_empty_diff(tmp_path: Path) -> None:
    """(b) ALL repos empty_diff -> entry 'empty_diff'."""
    repos = [_repo("empty_diff"), _repo("empty_diff", url=URL_B)]
    ctx = _make_ctx(tmp_path, repos)
    finalize_entry(ctx)
    assert ctx.entry_state.done_reason == "empty_diff"
    assert ctx.entry_state.status == "done"


def test_mixed_error_and_skip_no_diff(tmp_path: Path) -> None:
    """(c) 'already_latest' + 'error', no diff -> entry error."""
    repos = [
        _repo("already_latest"),
        _repo("error", "clone failed", url=URL_B),
    ]
    ctx = _make_ctx(tmp_path, repos)
    ctx.input_fn = lambda _: "c"
    finalize_entry(ctx)
    assert ctx.entry_state.status == "error"
    assert ctx.entry_state.done_reason is None


def test_mixed_non_error_no_changes_needed(tmp_path: Path) -> None:
    """(d) 'already_latest' + 'empty_diff' -> 'no_changes_needed'."""
    repos = [
        _repo("already_latest"),
        _repo("empty_diff", url=URL_B),
    ]
    ctx = _make_ctx(tmp_path, repos)
    finalize_entry(ctx)
    assert ctx.entry_state.done_reason == "no_changes_needed"
    assert ctx.entry_state.status == "done"


def test_partial_tier1_failure(tmp_path: Path) -> None:
    """(e) One repo errors, one succeeds, Tier 2 done -> partial."""
    repos = [
        _repo("error", "clone failed"),
        _repo(None, url=URL_B),
    ]
    ctx = _make_ctx(tmp_path, repos)
    for key in ("security_review", "upgrade_analysis", "upgrade_report",
            "graph_update", "validate_outputs"):
        ctx.entry_state.tasks_completed[key] = True
    finalize_entry(ctx)
    assert ctx.entry_state.status == "done"
    assert ctx.entry_state.done_reason == "partial"
    assert URL_A in ctx.entry_state.notes
