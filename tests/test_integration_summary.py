"""Integration tests for Summary stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.finalization import dispatch_summary_stage
from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.graph_entry import add_entry
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _setup_summary(tmp_path: Path) -> tuple[GlobalState, Path]:
    """Create state, graph, and review files for summary tests."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir(exist_ok=True)
    (tmp_path / ".tmp").mkdir(exist_ok=True)
    names = ["soma-dash-init.el", "soma-magit-init.el"]
    gs = GlobalState(
        emacs_version="28.1",
        entry_names=names,
    )
    gs.phases.setup = "done"
    gs.phases.entry_processing = "done"
    gs.phases.graph_finalization = "done"
    gs_path = state_dir / "global.json"
    atomic_write_json(gs_path, gs)
    for name in names:
        es = EntryState(
            init_file=name,
            repos=[RepoState(
                repo_url="https://github.com/test/repo",
                pinned_ref="abc123",
            )],
            status="done",
        )
        atomic_write_json(state_dir / f"{name}.json", es)
    (tmp_path / "soma-dash-init.el-security-review.md").write_text(
        "# Review\n\nRisk Rating: high\n", encoding="utf-8",
    )
    (tmp_path / "soma-magit-init.el-security-review.md").write_text(
        "# Review\n\nRisk Rating: low\n", encoding="utf-8",
    )
    graph: dict = {}
    add_entry(graph, "soma-dash-init.el", [
        {"package": "dash", "repo_url": "https://github.com/test/dash",
         "min_emacs_version": "26.1", "depends_on": []},
    ])
    add_entry(graph, "soma-magit-init.el", [
        {"package": "magit", "repo_url": "https://github.com/test/magit",
         "min_emacs_version": "29.1", "depends_on": ["dash"]},
    ])
    graph_path = tmp_path / "soma-inits-dependency-graphs.json"
    write_graph(graph_path, graph)
    return gs, gs_path


def test_summary_writes_security_summary(tmp_path: Path) -> None:
    """Summary stage writes security review summary grouped by rating."""
    gs, gs_path = _setup_summary(tmp_path)
    dispatch_summary_stage(gs, gs_path, tmp_path)
    summary_path = tmp_path / "security-review-summary.md"
    assert summary_path.exists()
    text = summary_path.read_text(encoding="utf-8")
    assert "## High" in text
    assert "## Low" in text


def test_summary_writes_version_conflicts(tmp_path: Path) -> None:
    """Summary stage writes version conflicts when Emacs is too old."""
    gs, gs_path = _setup_summary(tmp_path)
    dispatch_summary_stage(gs, gs_path, tmp_path)
    conflicts_path = tmp_path / "emacs-version-conflicts.md"
    assert conflicts_path.exists()
    text = conflicts_path.read_text(encoding="utf-8")
    assert "magit" in text
    assert "29.1" in text


def test_summary_marks_complete(tmp_path: Path) -> None:
    """Summary stage sets completed flag and date."""
    gs, gs_path = _setup_summary(tmp_path)
    dispatch_summary_stage(gs, gs_path, tmp_path)
    assert gs.completed is True
    assert gs.date_completed is not None
    assert gs.phases.summary == "done"


def test_summary_skips_when_done(tmp_path: Path) -> None:
    """Summary stage is skipped when already done."""
    gs, gs_path = _setup_summary(tmp_path)
    gs.phases.summary = "done"
    atomic_write_json(gs_path, gs)
    dispatch_summary_stage(gs, gs_path, tmp_path)
    assert gs.completed is False
