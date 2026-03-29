"""Entry change detection: new, modified, and orphaned entry handling, retry logic."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.state_creation import create_entry_state_if_missing
from soma_inits_upgrades.state_lifecycle import reset_entry_state_if_modified

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def detect_entry_changes(
    results: list[GroupedEntryDict], state_dir: Path, output_dir: Path,
) -> tuple[list[str], list[str]]:
    """Detect new and modified entries. Returns (new_names, modified_names)."""
    new: list[str] = []
    modified: list[str] = []
    for entry in results:
        if create_entry_state_if_missing(entry, state_dir):
            new.append(entry["init_file"])
        if reset_entry_state_if_modified(entry, state_dir, output_dir):
            modified.append(entry["init_file"])
    return new, modified


def handle_orphaned_entries(
    results: list[GroupedEntryDict], state_dir: Path,
    output_dir: Path, global_state: GlobalState,
) -> int:
    """Remove entries no longer in the input file.

    Deletes state files, output files, and graph entries for orphans.
    Returns the count of orphans removed.
    """
    from soma_inits_upgrades.graph import read_graph, write_graph
    from soma_inits_upgrades.graph_entry import remove_entries
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts

    current_names = {e["init_file"] for e in results}
    orphans = [n for n in global_state.entry_names if n not in current_names]
    if not orphans:
        return 0
    for name in orphans:
        (state_dir / f"{name}.json").unlink(missing_ok=True)
        delete_entry_artifacts(name, output_dir, include_permanent=True, include_temp=True)
        global_state.entry_names.remove(name)
        print(f"Entry {name} no longer in input file, removing", file=sys.stderr)
    graph_path = output_dir / "soma-inits-dependency-graphs.json"
    graph, _restored = read_graph(graph_path)
    remove_entries(graph, orphans)
    write_graph(graph_path, graph)
    return len(orphans)


def detect_new_or_modified_entries(
    results: list[GroupedEntryDict], state_dir: Path,
    output_dir: Path, global_state: GlobalState,
) -> tuple[list[str], list[str], int]:
    """Detect new, modified, and orphaned entries.

    Returns (new_entry_names, modified_entry_names, orphan_count).
    """
    new_names, modified_names = detect_entry_changes(results, state_dir, output_dir)
    orphan_count = handle_orphaned_entries(results, state_dir, output_dir, global_state)
    return new_names, modified_names, orphan_count

