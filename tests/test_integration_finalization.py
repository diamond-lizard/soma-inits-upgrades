"""Integration tests for Graph Finalization stage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.finalization import dispatch_graph_finalization
from soma_inits_upgrades.graph import add_entry, write_graph
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def _setup_graph_finalization(
    tmp_path: Path,
) -> tuple[GlobalState, Path, Path]:
    """Create state and graph files for graph finalization tests."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    (tmp_path / ".tmp").mkdir()
    gs = GlobalState(
        emacs_version="29.1",
        phases=GlobalState.model_fields["phases"].default_factory(),
        entry_names=["soma-dash-init.el", "soma-magit-init.el"],
    )
    gs.phases.setup = "done"
    gs.phases.entry_processing = "done"
    gs_path = state_dir / "global.json"
    atomic_write_json(gs_path, gs)
    graph: dict = {}
    add_entry(graph, "soma-dash-init.el", "dash", "26.1", [])
    add_entry(graph, "soma-magit-init.el", "magit", "27.1", ["dash"])
    graph_path = tmp_path / "soma-inits-dependency-graphs.json"
    write_graph(graph_path, graph)
    return gs, gs_path, graph_path


def test_graph_finalization_populates_depended_on_by(
    tmp_path: Path,
) -> None:
    """Graph Finalization inverts depends_on and validates the graph."""
    gs, gs_path, graph_path = _setup_graph_finalization(tmp_path)
    dispatch_graph_finalization(gs, gs_path, tmp_path)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["soma-dash-init.el"]["depended_on_by"] == ["magit"]
    assert graph["soma-magit-init.el"]["depended_on_by"] == []
    assert gs.phases.graph_finalization == "done"
    assert gs.graph_finalization_tasks.inversion is True
    assert gs.graph_finalization_tasks.validation is True
    assert gs.graph_finalization_tasks.completion is True


def test_graph_finalization_skips_when_done(tmp_path: Path) -> None:
    """Graph Finalization is skipped when already done."""
    gs, gs_path, _graph_path = _setup_graph_finalization(tmp_path)
    gs.phases.graph_finalization = "done"
    atomic_write_json(gs_path, gs)
    dispatch_graph_finalization(gs, gs_path, tmp_path)
    assert gs.phases.graph_finalization == "done"


def test_graph_finalization_writes_warnings(tmp_path: Path) -> None:
    """Graph Finalization writes warnings file when validation issues exist."""
    gs, gs_path, graph_path = _setup_graph_finalization(tmp_path)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    add_entry(graph, "soma-dup-init.el", "dash", None, [])
    write_graph(graph_path, graph)
    dispatch_graph_finalization(gs, gs_path, tmp_path)
    warnings_path = tmp_path / "dependency-graph-warnings.md"
    assert warnings_path.exists()
    text = warnings_path.read_text(encoding="utf-8")
    assert "Duplicate" in text
