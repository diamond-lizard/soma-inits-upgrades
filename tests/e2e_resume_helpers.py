"""Shared helpers for resume self-heal integration tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def make_all_done_global(
    state_dir: Path, entry_names: list[str],
) -> GlobalState:
    """Build a GlobalState where everything is completed."""
    gs = GlobalState(
        entry_names=entry_names,
        entries_summary={
            "total": len(entry_names),
            "done": len(entry_names),
        },
    )
    gs.phases.setup = "done"
    gs.phases.entry_processing = "done"
    gs.phases.graph_finalization = "done"
    gs.phases.summary = "done"
    gs.completed = True
    atomic_write_json(state_dir / "global.json", gs)
    return gs


def write_graph(output_dir: Path, keys: list[str]) -> None:
    """Write a graph file with stub entries for the given keys."""
    graph = {k: {"depends_on": []} for k in keys}
    path = output_dir / "soma-inits-dependency-graphs.json"
    path.write_text(json.dumps(graph), encoding="utf-8")


def results_for(names: list[str]) -> list[dict]:
    """Build minimal results list matching entry names."""
    return [
        {"init_file": n, "repos": [{"repo_url": "u", "pinned_ref": "a"}]}
        for n in names
    ]
