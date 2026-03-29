"""Tests for state_lifecycle.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import (
    atomic_write_json,
    mark_task_complete,
    read_entry_state,
    reconcile_entries_summary,
    reset_task,
)
from soma_inits_upgrades.state_lifecycle import detect_entry_field_changes
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_reconcile_entries_summary(tmp_path: Path) -> None:
    """Verify correct counting of per-entry states by status."""
    state_dir = tmp_path
    e1 = EntryState(
        init_file="a.el",
        repos=[RepoState(repo_url="https://x/y", pinned_ref="1")],
        status="done",
    )
    e2 = EntryState(
        init_file="b.el",
        repos=[RepoState(repo_url="https://x/z", pinned_ref="2")],
        status="error",
    )
    atomic_write_json(state_dir / "a.el.json", e1)
    atomic_write_json(state_dir / "b.el.json", e2)
    summary = reconcile_entries_summary(["a.el", "b.el", "c.el"], state_dir)
    assert summary.total == 3
    assert summary.done == 1
    assert summary.error == 1
    assert summary.pending == 1


def test_detect_entry_field_changes() -> None:
    """Verify field change detection."""
    state = EntryState(
        init_file="a.el",
        repos=[RepoState(
            repo_url="https://old", pinned_ref="old_ref",
        )],
    )
    no_change: dict[str, object] = {"init_file": "a.el",
        "repos": [{"repo_url": "https://old",
            "pinned_ref": "old_ref"}]}
    assert detect_entry_field_changes(state, no_change) == []
    url_change: dict[str, object] = {"init_file": "a.el",
        "repos": [{"repo_url": "https://new",
            "pinned_ref": "old_ref"}]}
    assert detect_entry_field_changes(state, url_change) == ["repos"]
    ref_change: dict[str, object] = {"init_file": "a.el",
        "repos": [{"repo_url": "https://old",
            "pinned_ref": "new_ref"}]}
    assert detect_entry_field_changes(state, ref_change) == ["repos"]
    both_change: dict[str, object] = {"init_file": "a.el",
        "repos": [{"repo_url": "https://new",
            "pinned_ref": "new_ref"}]}
    changes = detect_entry_field_changes(state, both_change)
    assert changes == ["repos"]


def test_read_entry_state_and_task_ops(tmp_path: Path) -> None:
    """Verify entry state read, task completion, and task reset."""
    path = tmp_path / "entry.json"
    state = EntryState(
        init_file="soma-dash-init.el",
        repos=[RepoState(
            repo_url="https://github.com/magnars/dash.el",
            pinned_ref="abc123",
        )],
    )
    atomic_write_json(path, state)
    loaded = read_entry_state(path)
    assert loaded is not None
    assert loaded.tasks_completed["security_review"] is False
    mark_task_complete(loaded, "security_review", path)
    reloaded = read_entry_state(path)
    assert reloaded is not None
    assert reloaded.tasks_completed["security_review"] is True
    reset_task(reloaded, "security_review", path)
    final = read_entry_state(path)
    assert final is not None
    assert final.tasks_completed["security_review"] is False

