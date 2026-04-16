"""Edge-case tests for scan_completed_entries_for_selfheal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from monorepo_test_helpers import make_init_file
from selfheal_scan_test_helpers import make_done_entry

from soma_inits_upgrades.selfheal_package_scan import (
    scan_completed_entries_for_selfheal,
)
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_in_progress_entry_skipped(tmp_path: Path) -> None:
    """Non-done entries are not scanned even if mismatched."""
    sd = tmp_path / ".state"
    sd.mkdir()
    inits = tmp_path / "inits"
    make_init_file(inits, "soma-dash-init.el", ["dash"])
    es = EntryState(
        init_file="soma-dash-init.el",
        repos=[RepoState(
            repo_url="https://forge.test/r",
            pinned_ref="a",
            package_name="dash-functional",
        )],
    )
    es.status = "in_progress"
    atomic_write_json(sd / "soma-dash-init.el.json", es)

    result = scan_completed_entries_for_selfheal(
        ["soma-dash-init.el"], sd, inits,
    )

    assert result == []


def test_none_inits_dir_returns_empty(tmp_path: Path) -> None:
    """inits_dir=None returns empty list immediately."""
    sd = tmp_path / ".state"
    sd.mkdir()
    make_done_entry(sd, "soma-dash-init.el", "dash-functional")

    result = scan_completed_entries_for_selfheal(
        ["soma-dash-init.el"], sd, None,
    )

    assert result == []


def test_missing_init_file_skipped(tmp_path: Path) -> None:
    """Entry whose init file does not exist on disk is skipped."""
    sd = tmp_path / ".state"
    sd.mkdir()
    inits = tmp_path / "inits"
    inits.mkdir()
    make_done_entry(sd, "soma-gone-init.el", "gone-pkg")

    result = scan_completed_entries_for_selfheal(
        ["soma-gone-init.el"], sd, inits,
    )

    assert result == []


def test_missing_state_file_skipped(tmp_path: Path) -> None:
    """Entry whose state file does not exist is skipped."""
    sd = tmp_path / ".state"
    sd.mkdir()
    inits = tmp_path / "inits"
    make_init_file(inits, "soma-dash-init.el", ["dash"])

    result = scan_completed_entries_for_selfheal(
        ["soma-dash-init.el"], sd, inits,
    )

    assert result == []
