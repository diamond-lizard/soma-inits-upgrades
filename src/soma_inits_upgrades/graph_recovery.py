"""Graph recovery: rebuild graph entries from state files."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.graph import GraphDict
    from soma_inits_upgrades.validation_schema import FlatEntryDict


def recover_single_graph_entry(
    init_file: str, graph: GraphDict, state_dir: Path,
    results: list[FlatEntryDict], output_dir: Path,
) -> bool:
    """Recover a single entry's graph data. Returns True if rerun needed."""
    from soma_inits_upgrades.state import read_entry_state
    from soma_inits_upgrades.state_creation import create_entry_state_if_missing

    path = state_dir / f"{init_file}.json"
    state = read_entry_state(path)
    if state is not None and any(r.package_name for r in state.repos):
        from soma_inits_upgrades.graph_entry import add_entry

        packages = [
            {
                "package": r.package_name or init_file,
                "repo_url": r.repo_url,
                "depends_on": r.depends_on or [],
                "min_emacs_version": r.min_emacs_version,
            }
            for r in state.repos
            if r.package_name is not None
        ]
        add_entry(graph, init_file, packages)
        return False
    entry_dict = next(
        (e for e in results if e["init_file"] == init_file), None,
    )
    if entry_dict:
        create_entry_state_if_missing(entry_dict, state_dir)
    import pathlib

    prog = pathlib.Path(sys.argv[0]).name
    print(
        f"Warning: state file corrupt for {init_file}, recreating. "
        f"This entry will be fully reprocessed on next run of {prog}.",
        file=sys.stderr,
    )
    return True


def recover_graph_from_backup(
    graph: GraphDict, results: list[FlatEntryDict],
    state_dir: Path, output_dir: Path,
) -> tuple[GraphDict, bool]:
    """Rebuild missing graph entries from state files.

    Returns (graph, needs_rerun).
    """
    from soma_inits_upgrades.state import read_entry_state

    needs_rerun = False
    for entry in results:
        name = entry["init_file"]
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is None:
            continue
        if not state.tasks_completed.get("graph_update", False):
            continue
        if name in graph:
            continue
        if recover_single_graph_entry(
            name, graph, state_dir, results, output_dir,
        ):
            needs_rerun = True
    return graph, needs_rerun
