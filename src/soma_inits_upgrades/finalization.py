"""Graph Finalization and Summary stages: graph inversion, validation, summary reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState


def dispatch_graph_finalization(
    global_state: GlobalState, global_state_path: Path, output_dir: Path,
) -> None:
    """Dispatch Graph Finalization stage: inversion, validation, completion."""
    if global_state.phases.graph_finalization == "done":
        return
    from soma_inits_upgrades.state import atomic_write_json

    global_state.phases.graph_finalization = "in_progress"
    atomic_write_json(global_state_path, global_state)
    graph_path = output_dir / "soma-inits-dependency-graphs.json"
    _run_inversion(global_state, global_state_path, graph_path)
    _run_validation(global_state, global_state_path, graph_path, output_dir)
    _complete_graph_finalization(global_state, global_state_path)

def _run_inversion(
    global_state: GlobalState, global_state_path: Path, graph_path: Path,
) -> None:
    """Invert dependency graph if not already done."""
    if global_state.graph_finalization_tasks.inversion:
        return
    from soma_inits_upgrades.graph import read_graph, write_graph
    from soma_inits_upgrades.graph_inversion import invert_dependencies
    from soma_inits_upgrades.state import atomic_write_json

    graph, _ = read_graph(graph_path)
    invert_dependencies(graph)
    write_graph(graph_path, graph)
    global_state.graph_finalization_tasks.inversion = True
    atomic_write_json(global_state_path, global_state)


def _run_validation(
    global_state: GlobalState, global_state_path: Path,
    graph_path: Path, output_dir: Path,
) -> None:
    """Validate dependency graph if not already done."""
    if global_state.graph_finalization_tasks.validation:
        return
    from soma_inits_upgrades.graph import read_graph
    from soma_inits_upgrades.graph_validation import validate_graph
    from soma_inits_upgrades.state import atomic_write_json

    graph, _ = read_graph(graph_path)
    warnings = validate_graph(graph)
    if warnings:
        _write_warnings(warnings, output_dir / "dependency-graph-warnings.md")
    global_state.graph_finalization_tasks.validation = True
    atomic_write_json(global_state_path, global_state)


def _write_warnings(warnings: list[str], path: Path) -> None:
    """Write graph validation warnings to markdown file."""
    lines = ["# Dependency Graph Warnings", ""]
    lines.extend(f"- {w}" for w in warnings)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _complete_graph_finalization(
    global_state: GlobalState, global_state_path: Path,
) -> None:
    """Mark graph finalization as done."""
    if global_state.graph_finalization_tasks.completion:
        return
    from soma_inits_upgrades.state import atomic_write_json

    global_state.phases.graph_finalization = "done"
    global_state.graph_finalization_tasks.completion = True
    atomic_write_json(global_state_path, global_state)


def dispatch_summary_stage(
    global_state: GlobalState, global_state_path: Path,
    output_dir: Path, start_time: float | None = None,
) -> None:
    """Dispatch Summary stage: security summary, version conflicts, completion."""
    if global_state.phases.summary == "done":
        eprint("Plan is already complete.")
        return
    from soma_inits_upgrades.finalization_summary import run_summary_steps

    run_summary_steps(global_state, global_state_path, output_dir, start_time)
