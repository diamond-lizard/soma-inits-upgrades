"""Tests for phase_dispatch_resume.py: resume completed entry processing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

_URL = "https://forge.test/r"


def _entry(ref: str) -> dict[str, object]:
    return {"init_file": "x.el", "repos": [{"repo_url": _URL, "pinned_ref": ref}]}


def test_resume_returns_false_no_changes(tmp_path: Path) -> None:
    """Returns False when no changes and no retryable errors."""
    from soma_inits_upgrades.phase_dispatch_resume import resume_completed_entry_processing
    from soma_inits_upgrades.state_schema import GlobalState

    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        status="done",
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(entry_names=["x.el"])
    atomic_write_json(sd / "global.json", gs)
    gp = tmp_path / "soma-inits-dependency-graphs.json"
    gp.write_text("{}", encoding="utf-8")
    results = [_entry("a")]
    assert resume_completed_entry_processing(
        results, sd, tmp_path, gs,
    ) is False


def test_resume_returns_true_retryable_errors(tmp_path: Path) -> None:
    """Returns True when retryable errors exist."""
    from soma_inits_upgrades.phase_dispatch_resume import resume_completed_entry_processing
    from soma_inits_upgrades.state_schema import GlobalState

    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        status="error", retries_remaining=3,
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(entry_names=["x.el"])
    atomic_write_json(sd / "global.json", gs)
    gp = tmp_path / "soma-inits-dependency-graphs.json"
    gp.write_text("{}", encoding="utf-8")
    results = [_entry("a")]
    assert resume_completed_entry_processing(
        results, sd, tmp_path, gs,
    ) is True
