"""Tests for phase_dispatch.py: viability, resume, retry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.phase_dispatch import check_processing_viability
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntriesSummary, EntryState

if TYPE_CHECKING:
    from pathlib import Path


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
        repo_url="https://github.com/x/y",
        pinned_ref="abc",
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
        repo_url="https://github.com/x/y",
        pinned_ref="abc",
        status="error",
        notes="timeout during clone",
    )
    atomic_write_json(state_dir / "a.el.json", errored)
    summary = EntriesSummary(total=1, done=0, error=1)
    with pytest.raises(SystemExit):
        check_processing_viability(summary, ["a.el"], state_dir)
    captured = capsys.readouterr()
    assert "timeout during clone" in captured.err


def test_resume_returns_false_no_changes(tmp_path: Path) -> None:
    """Returns False when no changes and no retryable errors."""
    from soma_inits_upgrades.phase_dispatch import resume_completed_entry_processing
    from soma_inits_upgrades.state_schema import GlobalState

    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    es = EntryState(
        init_file="x.el", repo_url="https://x.com/r", pinned_ref="a",
        status="done",
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(entry_names=["x.el"])
    atomic_write_json(sd / "global.json", gs)
    gp = tmp_path / "soma-inits-dependency-graphs.json"
    gp.write_text("{}", encoding="utf-8")
    results = [{"init_file": "x.el", "repo_url": "https://x.com/r", "pinned_ref": "a"}]
    assert resume_completed_entry_processing(results, sd, tmp_path, gs) is False


def test_resume_returns_true_retryable_errors(tmp_path: Path) -> None:
    """Returns True when retryable errors exist."""
    from soma_inits_upgrades.phase_dispatch import resume_completed_entry_processing
    from soma_inits_upgrades.state_schema import GlobalState

    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    es = EntryState(
        init_file="x.el", repo_url="https://x.com/r", pinned_ref="a",
        status="error", retries_remaining=3,
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(entry_names=["x.el"])
    atomic_write_json(sd / "global.json", gs)
    gp = tmp_path / "soma-inits-dependency-graphs.json"
    gp.write_text("{}", encoding="utf-8")
    results = [{"init_file": "x.el", "repo_url": "https://x.com/r", "pinned_ref": "a"}]
    assert resume_completed_entry_processing(results, sd, tmp_path, gs) is True
