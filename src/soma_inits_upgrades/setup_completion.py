"""Setup stage completion: dependency graph init and stage finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import FlatEntryDict


def initialize_dep_graph(graph_path: Path) -> None:
    """Create the dependency graph file if it does not exist.

    If it exists, reads and preserves it (validation happens later).
    If missing, writes an empty JSON object.
    """
    from soma_inits_upgrades.graph import read_graph, write_graph

    graph, _restored = read_graph(graph_path)
    if not graph_path.exists():
        write_graph(graph_path, graph)


def complete_setup(
    global_state: GlobalState,
    global_state_path: Path,
    results: list[FlatEntryDict],
) -> None:
    """Finalize the setup stage.

    Populates entry_names, reconciles entries_summary, sets
    current_entry to the first pending or in-progress entry, and
    marks phases.setup as done.
    """
    from soma_inits_upgrades.state import atomic_write_json, reconcile_entries_summary

    state_dir = global_state_path.parent
    entry_names = [e["init_file"] for e in results]
    global_state.entry_names = entry_names
    global_state.entries_summary = reconcile_entries_summary(entry_names, state_dir)
    global_state.current_entry = _first_actionable_entry(entry_names, state_dir)
    global_state.phases.setup = "done"
    atomic_write_json(global_state_path, global_state)


def _first_actionable_entry(
    entry_names: list[str], state_dir: Path,
) -> str | None:
    """Return the first entry with pending or in_progress status."""
    from soma_inits_upgrades.state import read_entry_state

    for name in entry_names:
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is None or state.status in ("pending", "in_progress"):
            return name
    return None


def initialize_entry_states(
    results: list[FlatEntryDict],
    state_dir: Path,
    output_dir: Path,
    global_state: GlobalState,
) -> tuple[int, int]:
    """Initialize per-entry state files and reset downstream if needed.

    Returns (created_count, modified_count).
    """
    from soma_inits_upgrades.state_creation import create_entry_state_if_missing
    from soma_inits_upgrades.state_lifecycle import (
        reset_downstream_phases,
        reset_entry_state_if_modified,
    )

    created = modified = 0
    for entry in results:
        if create_entry_state_if_missing(entry, state_dir):
            created += 1
        if reset_entry_state_if_modified(entry, state_dir, output_dir):
            modified += 1
    if modified > 0:
        reset_downstream_phases(global_state)
    return created, modified
