"""Tests for phase_dispatch.py: viability, resume, retry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.phase_dispatch import check_processing_viability
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntriesSummary, EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


_URL = "https://forge.test/r"


def _entry(ref: str) -> dict[str, object]:
    return {"init_file": "x.el", "repos": [{"repo_url": _URL, "pinned_ref": ref}]}

def test_viability_passes_with_done_entries(tmp_path: Path) -> None:
    """Returns normally when at least one entry succeeded."""
    summary = EntriesSummary(total=2, done=1, error=1)
    check_processing_viability(summary, ["a.el", "b.el"], tmp_path)


def test_viability_fails_with_zero_done(tmp_path: Path) -> None:
    """Exits with code 1 when no entries succeeded."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    errored = EntryState(
        init_file="a.el",
        repos=[RepoState(
            repo_url="https://github.com/x/y",
            pinned_ref="abc",
        )],
        status="error",
        notes="clone failed",
    )
    atomic_write_json(state_dir / "a.el.json", errored)
    summary = EntriesSummary(total=1, done=0, error=1)
    with pytest.raises(SystemExit) as exc_info:
        check_processing_viability(summary, ["a.el"], state_dir)
    assert exc_info.value.code == 1


def test_viability_prints_error_notes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Error notes are printed to stderr on viability failure."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    errored = EntryState(
        init_file="a.el",
        repos=[RepoState(
            repo_url="https://github.com/x/y",
            pinned_ref="abc",
        )],
        status="error",
        notes="timeout during clone",
    )
    atomic_write_json(state_dir / "a.el.json", errored)
    summary = EntriesSummary(total=1, done=0, error=1)
    with pytest.raises(SystemExit):
        check_processing_viability(summary, ["a.el"], state_dir)
    captured = capsys.readouterr()
    assert "timeout during clone" in captured.err

