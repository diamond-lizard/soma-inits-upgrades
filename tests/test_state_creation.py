"""Tests for state_creation.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state_creation import create_entry_state_if_missing

if TYPE_CHECKING:
    from pathlib import Path


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
