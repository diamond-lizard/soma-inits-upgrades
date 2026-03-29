#!/usr/bin/env python3
"""Tests for retry with two-tier repo done_reason reset."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _repo(done_reason: str | None = None, notes: str | None = None) -> RepoState:
    """Build a RepoState with optional done_reason and notes."""
    return RepoState(
        repo_url="https://github.com/magnars/dash.el",
        pinned_ref="abc1234567890abcdef1234567890abcdef123456",
        done_reason=done_reason,
        notes=notes,
    )


def test_retry_resets_repo_done_reason(tmp_path: Path) -> None:
    """Retry resets repo done_reason for errored repos only."""
    from soma_inits_upgrades.entry_retry import retry_errored_entries
    from soma_inits_upgrades.state import atomic_write_json, read_entry_state
    from soma_inits_upgrades.state_schema import EntryState
    state_dir = tmp_path / ".state"
    state_dir.mkdir(exist_ok=True)
    es = EntryState(
        init_file="x.el", repos=[_repo("error", "clone failed")],
        status="error", done_reason="error", notes="clone failed",
    )
    atomic_write_json(state_dir / "x.el.json", es)
    results = [{"init_file": "x.el", "repos": [{"repo_url": "u", "pinned_ref": "p"}]}]
    retry_errored_entries(results, state_dir)
    reloaded = read_entry_state(state_dir / "x.el.json")
    assert reloaded is not None
    assert reloaded.repos[0].done_reason is None
    assert reloaded.done_reason is None
