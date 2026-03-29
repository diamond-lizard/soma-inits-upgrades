#!/usr/bin/env python3
"""Tests for processing_finalize: two-tier completion semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.processing_finalize import finalize_entry
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _repo(done_reason: str | None = None, notes: str | None = None) -> RepoState:
    """Build a RepoState with optional done_reason and notes."""
    r = RepoState(
        repo_url="https://github.com/magnars/dash.el",
        pinned_ref="abc1234567890abcdef1234567890abcdef123456",
    )
    r.done_reason = done_reason
    r.notes = notes
    return r


def _make_ctx(tmp_path: Path, repo: RepoState):
    """Build an in-progress EntryContext with one repo."""
    from runner_helpers import make_ctx
    ctx = make_ctx(tmp_path, [repo])
    ctx.entry_state.status = "in_progress"
    return ctx


def test_already_latest_passthrough(tmp_path: Path) -> None:
    """(a)(c) Repo 'already_latest' passes through; entry done via branch a."""
    ctx = _make_ctx(tmp_path, _repo("already_latest"))
    finalize_entry(ctx)
    assert ctx.entry_state.done_reason == "already_latest"
    assert ctx.entry_state.status == "done"
    assert not any(ctx.entry_state.tasks_completed[k] for k in (
        "security_review", "upgrade_analysis", "upgrade_report",
        "graph_update", "validate_outputs",
    ))


def test_empty_diff_passthrough(tmp_path: Path) -> None:
    """(b) Repo 'empty_diff' passes through; entry done via branch a."""
    ctx = _make_ctx(tmp_path, _repo("empty_diff"))
    finalize_entry(ctx)
    assert ctx.entry_state.done_reason == "empty_diff"
    assert ctx.entry_state.status == "done"


def test_normal_completion_branch_b(tmp_path: Path) -> None:
    """(c2) Repo with no done_reason + all Tier 2 complete -> entry done."""
    ctx = _make_ctx(tmp_path, _repo(None))
    for key in ("security_review", "upgrade_analysis", "upgrade_report",
                "graph_update", "validate_outputs"):
        ctx.entry_state.tasks_completed[key] = True
    finalize_entry(ctx)
    assert ctx.entry_state.done_reason is None
    assert ctx.entry_state.status == "done"



def test_repo_error_sets_entry_error(tmp_path: Path) -> None:
    """(e) Repo done_reason 'error' -> entry status 'error'."""
    ctx = _make_ctx(tmp_path, _repo("error", "clone failed"))
    finalize_entry(ctx)
    assert ctx.entry_state.status == "error"
    assert ctx.entry_state.done_reason == "error"
    assert ctx.global_state.entries_summary.error == 1
    assert ctx.global_state.entries_summary.in_progress == 0


def test_guard_preserves_skipped(tmp_path: Path) -> None:
    """(f) GUARD: entry already 'done'/'skipped' is preserved."""
    ctx = _make_ctx(tmp_path, _repo(None))
    ctx.entry_state.status = "done"
    ctx.entry_state.done_reason = "skipped"
    ctx.entry_state.notes = "skipped by user at security_review step"
    finalize_entry(ctx)
    assert ctx.entry_state.status == "done"
    assert ctx.entry_state.done_reason == "skipped"
