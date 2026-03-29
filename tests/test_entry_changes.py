"""Tests for entry_changes.py: change detection, orphans, retry logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_changes import (
    detect_entry_changes,
    handle_orphaned_entries,
)
from soma_inits_upgrades.entry_retry import retry_errored_entries
from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _write_entry(sd: Path, name: str, **kw: object) -> None:
    """Write an entry state file."""
    es = EntryState(
        init_file=name,
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        **kw,
    )
    atomic_write_json(sd / f"{name}.json", es)


def test_detect_new_entries(tmp_path: Path) -> None:
    """New entries appear in new_entry_names."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"}]
    new, modified = detect_entry_changes(results, sd, tmp_path)
    assert new == ["x.el"]
    assert modified == []


def test_detect_modified_entries(tmp_path: Path) -> None:
    """Modified entries appear in modified_entry_names."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    _write_entry(sd, "x.el")
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "b"}]
    new, modified = detect_entry_changes(results, sd, tmp_path)
    assert new == []
    assert modified == ["x.el"]


def test_detect_unchanged(tmp_path: Path) -> None:
    """Unchanged entries appear in neither list."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    _write_entry(sd, "x.el")
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"}]
    new, modified = detect_entry_changes(results, sd, tmp_path)
    assert new == [] and modified == []


def test_handle_orphaned_entries(tmp_path: Path) -> None:
    """Orphaned entries are removed from state and graph."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    _write_entry(sd, "old.el")
    gs = GlobalState(entry_names=["old.el"])
    gp = tmp_path / "soma-inits-dependency-graphs.json"
    write_graph(gp, {"old.el": {
        "packages": [{"package": "old", "repo_url": "https://github.com/t/old",
                      "depends_on": [], "min_emacs_version": None}],
        "depended_on_by": [],
    }})
    count = handle_orphaned_entries([], sd, tmp_path, gs)
    assert count == 1
    assert "old.el" not in gs.entry_names
    assert not (sd / "old.el.json").exists()


def test_retry_errored_with_retries(tmp_path: Path) -> None:
    """Errored entries with retries are reset to in_progress."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
    )
    es.status = "error"
    es.retries_remaining = 3
    es.notes = "some error"
    es.tasks_completed["clone"] = True
    atomic_write_json(sd / "x.el.json", es)
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"}]
    count = retry_errored_entries(results, sd)
    assert count == 1
    from soma_inits_upgrades.state import read_entry_state
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.status == "in_progress"
    assert state.retries_remaining == 2
    assert state.tasks_completed["clone"] is True


def test_retry_exhausted(tmp_path: Path) -> None:
    """Errored entries with no retries are skipped."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
    )
    es.status = "error"
    es.retries_remaining = 0
    atomic_write_json(sd / "x.el.json", es)
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"}]
    count = retry_errored_entries(results, sd)
    assert count == 0
