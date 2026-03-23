"""Tests for state.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import (
    atomic_write_json,
    create_entry_state_if_missing,
    detect_entry_field_changes,
    mark_task_complete,
    read_entry_state,
    read_global_state,
    reconcile_entries_summary,
    reset_task,
)
from soma_inits_upgrades.state_schema import EntryState, GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def test_global_state_defaults() -> None:
    """Verify GlobalState() with no arguments has expected defaults."""
    gs = GlobalState()
    assert gs.phases.setup == "pending"
    assert gs.completed is False
    assert gs.entry_names == []


def test_atomic_write_and_read_global(tmp_path: Path) -> None:
    """Verify atomic write creates file and read returns valid state."""
    path = tmp_path / "global.json"
    gs = GlobalState(emacs_version="29.1")
    atomic_write_json(path, gs)
    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
    loaded = read_global_state(path)
    assert loaded is not None
    assert loaded.emacs_version == "29.1"


def test_read_global_state_missing(tmp_path: Path) -> None:
    """Verify read returns None for missing file."""
    assert read_global_state(tmp_path / "nope.json") is None


def test_read_global_state_invalid_json(tmp_path: Path) -> None:
    """Verify read returns None for invalid JSON."""
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    assert read_global_state(path) is None


def test_read_global_state_fills_defaults(tmp_path: Path) -> None:
    """Verify Pydantic fills missing fields with defaults."""
    path = tmp_path / "partial.json"
    path.write_text('{"emacs_version": "28.2"}', encoding="utf-8")
    loaded = read_global_state(path)
    assert loaded is not None
    assert loaded.emacs_version == "28.2"
    assert loaded.phases.setup == "pending"
    assert loaded.completed is False


def test_read_entry_state_and_task_ops(tmp_path: Path) -> None:
    """Verify entry state read, task completion, and task reset."""
    path = tmp_path / "entry.json"
    state = EntryState(
        init_file="soma-dash-init.el",
        repo_url="https://github.com/magnars/dash.el",
        pinned_ref="abc123",
    )
    atomic_write_json(path, state)
    loaded = read_entry_state(path)
    assert loaded is not None
    assert loaded.tasks_completed["clone"] is False
    mark_task_complete(loaded, "clone", path)
    reloaded = read_entry_state(path)
    assert reloaded is not None
    assert reloaded.tasks_completed["clone"] is True
    reset_task(reloaded, "clone", path)
    final = read_entry_state(path)
    assert final is not None
    assert final.tasks_completed["clone"] is False


def test_read_entry_state_invalid(tmp_path: Path) -> None:
    """Verify read returns None for invalid entry state JSON."""
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    assert read_entry_state(path) is None


def test_create_entry_state_if_missing(tmp_path: Path) -> None:
    """Verify creation for missing states, no-op for valid states."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    entry = {
        "init_file": "soma-dash-init.el",
        "repo_url": "https://github.com/x/y",
        "pinned_ref": "abc",
    }
    assert create_entry_state_if_missing(entry, state_dir) is True
    assert (state_dir / "soma-dash-init.el.json").exists()
    assert create_entry_state_if_missing(entry, state_dir) is False


def test_create_entry_state_recreates_corrupt(tmp_path: Path) -> None:
    """Verify corrupt state file is recreated."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    path = state_dir / "soma-dash-init.el.json"
    path.write_text("corrupt!", encoding="utf-8")
    entry = {
        "init_file": "soma-dash-init.el",
        "repo_url": "https://github.com/x/y",
        "pinned_ref": "abc",
    }
    assert create_entry_state_if_missing(entry, state_dir) is True


def test_reconcile_entries_summary(tmp_path: Path) -> None:
    """Verify correct counting of per-entry states by status."""
    state_dir = tmp_path
    e1 = EntryState(init_file="a.el", repo_url="https://x/y", pinned_ref="1", status="done")
    e2 = EntryState(init_file="b.el", repo_url="https://x/z", pinned_ref="2", status="error")
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
        init_file="a.el", repo_url="https://old", pinned_ref="old_ref",
    )
    no_change = {"repo_url": "https://old", "pinned_ref": "old_ref"}
    assert detect_entry_field_changes(state, no_change) == []
    url_change = {"repo_url": "https://new", "pinned_ref": "old_ref"}
    assert detect_entry_field_changes(state, url_change) == ["repo_url"]
    ref_change = {"repo_url": "https://old", "pinned_ref": "new_ref"}
    assert detect_entry_field_changes(state, ref_change) == ["pinned_ref"]
    both_change = {"repo_url": "https://new", "pinned_ref": "new_ref"}
    changes = detect_entry_field_changes(state, both_change)
    assert "repo_url" in changes and "pinned_ref" in changes


def test_atomic_write_preserves_original_on_failure(tmp_path: Path) -> None:
    """Verify original file unchanged if .tmp write fails."""
    path = tmp_path / "test.json"
    gs = GlobalState(emacs_version="29.1")
    atomic_write_json(path, gs)
    original = path.read_text(encoding="utf-8")
    # Make tmp dir read-only to cause write failure
    import os
    os.chmod(tmp_path, 0o555)
    try:
        atomic_write_json(path, GlobalState(emacs_version="30.0"))
        raise AssertionError("Should have raised")
    except OSError:
        pass
    finally:
        os.chmod(tmp_path, 0o755)
    assert path.read_text(encoding="utf-8") == original
