"""Graph update tasks: dependency graph maintenance and recovery."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.graph import GraphDict
    from soma_inits_upgrades.protocols import EntryContext


def recover_single_graph_entry(
    init_file: str, graph: GraphDict, state_dir: Path,
    results: list[dict[str, str]], output_dir: Path,
) -> bool:
    """Recover a single entry's graph data. Returns True if rerun needed."""
    from soma_inits_upgrades.state import read_entry_state
    from soma_inits_upgrades.state_lifecycle import create_entry_state_if_missing

    path = state_dir / f"{init_file}.json"
    state = read_entry_state(path)
    if state is not None and state.package_name is not None:
        from soma_inits_upgrades.graph import add_entry

        add_entry(
            graph, init_file, state.package_name,
            state.min_emacs_version, state.depends_on or [],
        )
        return False
    entry_dict = next((e for e in results if e["init_file"] == init_file), None)
    if entry_dict:
        create_entry_state_if_missing(entry_dict, state_dir)
    import pathlib

    prog = pathlib.Path(sys.argv[0]).name
    print(
        f"Warning: state file corrupt for {init_file}, recreating. "
        f"This entry will be fully reprocessed on the next run of {prog}.",
        file=sys.stderr,
    )
    return True


def recover_graph_from_backup(
    graph: GraphDict, results: list[dict[str, str]],
    state_dir: Path, output_dir: Path,
) -> tuple[GraphDict, bool]:
    """Rebuild missing graph entries from state files. Returns (graph, needs_rerun)."""
    from soma_inits_upgrades.state import read_entry_state

    needs_rerun = False
    for entry in results:
        name = entry["init_file"]
        state = read_entry_state(state_dir / f"{name}.json")
        if state is None or not state.tasks_completed.get("graph_update", False):
            continue
        if name in graph:
            continue
        if recover_single_graph_entry(name, graph, state_dir, results, output_dir):
            needs_rerun = True
    return graph, needs_rerun


def task_graph_update(ctx: EntryContext) -> bool:
    """Update the dependency graph with this entry's data."""
    if ctx.entry_state.tasks_completed.get("graph_update", False):
        return False
    from soma_inits_upgrades.graph import add_entry, read_graph, write_graph
    from soma_inits_upgrades.processing_helpers import set_entry_error
    from soma_inits_upgrades.state import mark_task_complete

    graph_path = ctx.output_dir / "soma-inits-dependency-graphs.json"
    graph, restored = read_graph(graph_path)
    needs_rerun = False
    if restored:
        graph, needs_rerun = recover_graph_from_backup(
            graph, ctx.results, ctx.state_dir, ctx.output_dir,
        )
    pkg = ctx.entry_state.package_name or ctx.init_stem
    add_entry(graph, ctx.entry_state.init_file, pkg,
              ctx.entry_state.min_emacs_version, ctx.entry_state.depends_on or [])
    try:
        write_graph(graph_path, graph)
    except OSError as exc:
        set_entry_error(ctx, f"failed to update dependency graph: {exc}")
        return needs_rerun
    mark_task_complete(ctx.entry_state, "graph_update", ctx.entry_state_path)
    return needs_rerun
