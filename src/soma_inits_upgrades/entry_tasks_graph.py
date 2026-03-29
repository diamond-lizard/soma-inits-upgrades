"""Graph update task: add entry data to the dependency graph."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def task_graph_update(ctx: EntryContext) -> bool:
    """Update the dependency graph with this entry's data."""
    if ctx.entry_state.tasks_completed.get("graph_update", False):
        return False
    from soma_inits_upgrades.graph import read_graph, write_graph
    from soma_inits_upgrades.graph_entry import add_entry
    from soma_inits_upgrades.graph_recovery import recover_graph_from_backup
    from soma_inits_upgrades.processing_helpers import set_entry_error
    from soma_inits_upgrades.state import mark_task_complete

    graph_path = ctx.output_dir / "soma-inits-dependency-graphs.json"
    graph, restored = read_graph(graph_path)
    needs_rerun = False
    if restored:
        graph, needs_rerun = recover_graph_from_backup(
            graph, ctx.results, ctx.state_dir, ctx.output_dir,
        )
    packages = [
        {
            "package": r.package_name or ctx.init_stem,
            "repo_url": r.repo_url,
            "depends_on": r.depends_on or [],
            "min_emacs_version": r.min_emacs_version,
        }
        for r in ctx.entry_state.repos
        if r.done_reason is None
    ]
    add_entry(graph, ctx.entry_state.init_file, packages)
    try:
        write_graph(graph_path, graph)
    except OSError as exc:
        set_entry_error(ctx, f"failed to update dependency graph: {exc}")
        return needs_rerun
    mark_task_complete(
        ctx.entry_state, "graph_update", ctx.entry_state_path,
    )
    return needs_rerun
