"""Tests for entry_changes.py: change detection, orphans, retry logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_changes import (
    detect_entry_changes,
    handle_orphaned_entries,
)
from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

_URL = "https://forge.test/r"


def _entry(ref: str) -> dict[str, object]:
    return {"init_file": "x.el", "repos": [{"repo_url": _URL, "pinned_ref": ref}]}

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
    results = [_entry("a")]
    new, modified = detect_entry_changes(results, sd, tmp_path)
    assert new == ["x.el"]
    assert modified == []


def test_detect_modified_entries(tmp_path: Path) -> None:
    """Modified entries appear in modified_entry_names."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    _write_entry(sd, "x.el")
    results = [_entry("b")]
    new, modified = detect_entry_changes(results, sd, tmp_path)
    assert new == []
    assert modified == ["x.el"]


def test_detect_unchanged(tmp_path: Path) -> None:
    """Unchanged entries appear in neither list."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    _write_entry(sd, "x.el")
    results = [_entry("a")]
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

