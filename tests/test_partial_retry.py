#!/usr/bin/env python3
"""Tests for multi-repo partial/retry finalization behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
from soma_inits_upgrades.entry_retry import retry_errored_entries
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState

URL_A = "https://github.com/test/repo-a"
URL_B = "https://github.com/test/repo-b"
PIN = "abc1234567890abcdef1234567890abcdef123456"


def _write_state(
    state_dir: Path, name: str, repos: list[RepoState],
    status: str = "done", done_reason: str | None = None,
) -> None:
    """Write an entry state file with given repos and status."""
    es = EntryState(
        init_file=name, repos=repos,
        status=status, done_reason=done_reason,
    )
    atomic_write_json(state_dir / f"{name}.json", es)


def test_partial_entry_not_retried(tmp_path: Path) -> None:
    """(f) Entries with done_reason 'partial' are NOT retried."""
    sd = tmp_path
    repos = [
        RepoState(repo_url=URL_A, pinned_ref=PIN, done_reason="error"),
        RepoState(repo_url=URL_B, pinned_ref=PIN),
    ]
    _write_state(sd, "x.el", repos, status="done", done_reason="partial")
    results = [{"init_file": "x.el", "repos": [
        {"repo_url": URL_A, "pinned_ref": PIN},
        {"repo_url": URL_B, "pinned_ref": PIN},
    ]}]
    retried = retry_errored_entries(results, sd)
    assert retried == 0


def test_selective_repo_reset_on_retry(tmp_path: Path) -> None:
    """(g) Retry resets only errored repo, preserves non-errored repo."""
    sd = tmp_path
    ok_repo = RepoState(repo_url=URL_A, pinned_ref=PIN)
    ok_repo.done_reason = "already_latest"
    for k in ok_repo.tier1_tasks_completed:
        ok_repo.tier1_tasks_completed[k] = True
    err_repo = RepoState(repo_url=URL_B, pinned_ref=PIN)
    err_repo.done_reason = "error"
    for k in err_repo.tier1_tasks_completed:
        err_repo.tier1_tasks_completed[k] = True
    _write_state(sd, "x.el", [ok_repo, err_repo], status="error")
    results = [{"init_file": "x.el", "repos": [
        {"repo_url": URL_A, "pinned_ref": PIN},
        {"repo_url": URL_B, "pinned_ref": PIN},
    ]}]
    retried = retry_errored_entries(results, sd)
    assert retried == 1
    from soma_inits_upgrades.state import read_entry_state
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.status == "in_progress"
    r_ok = state.repos[0]
    assert r_ok.done_reason == "already_latest"
    assert all(r_ok.tier1_tasks_completed.values())
    r_err = state.repos[1]
    assert r_err.done_reason is None
    assert not any(r_err.tier1_tasks_completed.values())
