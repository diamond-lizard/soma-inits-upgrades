"""Tests for state_artifacts.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_artifacts import (
    delete_entry_artifacts,
    get_entry_artifact_paths,
)
from soma_inits_upgrades.state_lifecycle import reset_entry_state_if_modified
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_get_entry_artifact_paths() -> None:
    """Verify correct path categories are returned."""
    from pathlib import Path

    paths = get_entry_artifact_paths("soma-dash-init.el", Path("/out"))
    assert len(paths["permanent"]) == 5
    assert len(paths["temp"]) == 1
    assert paths["temp"][0] == Path("/out/.tmp/soma-dash-init")
    assert len(paths["state"]) == 1
    assert Path("/out/.state/soma-dash-init.el.json") in paths["state"]


def test_delete_entry_artifacts_temp_only(output_dir: Path) -> None:
    """Verify only temp files are deleted when include_permanent=False."""
    init_tmp = output_dir / ".tmp" / "soma-dash-init"
    init_tmp.mkdir(parents=True, exist_ok=True)
    diff_file = init_tmp / "soma-dash-init.diff"
    perm_file = output_dir / "soma-dash-init.el-security-review.md"
    diff_file.write_text("diff", encoding="utf-8")
    perm_file.write_text("review", encoding="utf-8")
    delete_entry_artifacts(
        "soma-dash-init.el", output_dir,
        include_permanent=False, include_temp=True,
    )
    assert not init_tmp.exists()
    assert perm_file.exists()


def test_delete_entry_artifacts_missing_files(output_dir: Path) -> None:
    """Verify FileNotFoundError is silently ignored."""
    delete_entry_artifacts("soma-dash-init.el", output_dir)


def test_reset_entry_state_if_modified_no_change(output_dir: Path) -> None:
    """Verify no-op when entry is unchanged."""
    state_dir = output_dir / ".state"
    entry = {
        "init_file": "soma-dash-init.el",
        "repo_url": "https://github.com/magnars/dash.el",
        "pinned_ref": "abc123",
    }
    state = EntryState(
        init_file=entry["init_file"],
        repos=[RepoState(
            repo_url=entry["repo_url"],
            pinned_ref=entry["pinned_ref"],
        )],
    )
    atomic_write_json(state_dir / "soma-dash-init.el.json", state)
    assert reset_entry_state_if_modified(entry, state_dir, output_dir) is False


def test_reset_entry_state_if_modified_url_change(output_dir: Path) -> None:
    """Verify reset when repo_url changes and artifacts are deleted."""
    state_dir = output_dir / ".state"
    old_state = EntryState(
        init_file="soma-dash-init.el",
        repos=[RepoState(
            repo_url="https://github.com/old/repo",
            pinned_ref="abc123",
        )],
    )
    atomic_write_json(state_dir / "soma-dash-init.el.json", old_state)
    perm_file = output_dir / "soma-dash-init.el-security-review.md"
    perm_file.write_text("old review", encoding="utf-8")
    entry = {
        "init_file": "soma-dash-init.el",
        "repo_url": "https://github.com/new/repo",
        "pinned_ref": "abc123",
    }
    result = reset_entry_state_if_modified(entry, state_dir, output_dir)
    assert result is True
    assert not perm_file.exists()
