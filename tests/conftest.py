"""Shared pytest fixtures for soma-inits-upgrades tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.state_schema import EntryState, GlobalState

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

@pytest.fixture()
def sample_stale_inits() -> list[dict[str, str]]:
    """Return a valid stale inits results list with 2 sample entries."""
    return [
        {
            "init_file": "soma-dash-init.el",
            "repo_url": "https://github.com/magnars/dash.el",
            "pinned_ref": "abc1234567890abcdef1234567890abcdef123456",
        },
        {
            "init_file": "soma-magit-init.el",
            "repo_url": "https://github.com/magit/magit",
            "pinned_ref": "def4567890abcdef1234567890abcdef12345678",
        },
    ]


@pytest.fixture()
def sample_entry_state() -> EntryState:
    """Return a default EntryState model instance."""
    return EntryState(
        init_file="soma-dash-init.el",
        repo_url="https://github.com/magnars/dash.el",
        pinned_ref="abc1234567890abcdef1234567890abcdef123456",
    )


@pytest.fixture()
def sample_global_state() -> GlobalState:
    """Return a default GlobalState model instance."""
    return GlobalState()


@pytest.fixture()
def output_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary output directory with .state/ and .tmp/ subdirectories."""
    state_dir = tmp_path / ".state"
    tmp_dir = tmp_path / ".tmp"
    state_dir.mkdir()
    tmp_dir.mkdir()
    yield tmp_path
