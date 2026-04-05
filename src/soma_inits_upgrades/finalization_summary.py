"""Summary stage steps: security summary, version conflicts, completion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState


def run_summary_steps(
    global_state: GlobalState, global_state_path: Path,
    output_dir: Path, start_time: float | None,
) -> None:
    """Execute summary sub-tasks: security summary, version conflicts, completion."""
    from soma_inits_upgrades.state import atomic_write_json

    global_state.phases.summary = "in_progress"
    atomic_write_json(global_state_path, global_state)
    _run_security_summary(global_state, global_state_path, output_dir)
    _run_version_conflicts(global_state, global_state_path, output_dir)
    _complete_summary(global_state, global_state_path, output_dir, start_time)


def _run_security_summary(
    global_state: GlobalState, global_state_path: Path, output_dir: Path,
) -> None:
    """Compile and write security summary if not already done."""
    if global_state.summary_tasks.security_summary:
        return
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.summary import (
        compile_security_summary,
        write_security_summary_report,
    )

    grouped = compile_security_summary(global_state.entry_names, output_dir)
    summary_path = output_dir / "security-review-summary.md"
    write_security_summary_report(grouped, summary_path)
    global_state.summary_tasks.security_summary = True
    atomic_write_json(global_state_path, global_state)


def _run_version_conflicts(
    global_state: GlobalState, global_state_path: Path, output_dir: Path,
) -> None:
    """Write version conflicts report if not already done."""
    if global_state.summary_tasks.version_conflicts:
        return
    from soma_inits_upgrades.graph import read_graph
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.summary_conflicts import write_version_conflicts

    graph_path = output_dir / "soma-inits-dependency-graphs.json"
    graph, _ = read_graph(graph_path)
    conflicts_path = output_dir / "emacs-version-conflicts.md"
    write_version_conflicts(
        graph, global_state.entry_names,
        global_state.emacs_version, conflicts_path,
    )
    global_state.summary_tasks.version_conflicts = True
    atomic_write_json(global_state_path, global_state)


def _complete_summary(
    global_state: GlobalState, global_state_path: Path,
    output_dir: Path, start_time: float | None,
) -> None:
    """Mark summary and overall run as complete, print completion message."""
    if global_state.summary_tasks.completion:
        return
    import time
    from datetime import date

    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.summary_completion import categorize_entries
    from soma_inits_upgrades.summary_format import format_completion_message

    global_state.phases.summary = "done"
    global_state.completed = True
    global_state.date_completed = date.today().isoformat()
    global_state.summary_tasks.completion = True
    atomic_write_json(global_state_path, global_state)
    state_dir = output_dir / ".state"
    categories = categorize_entries(global_state.entry_names, state_dir)
    elapsed = time.monotonic() - start_time if start_time is not None else None
    msg = format_completion_message(
        categories, len(global_state.entry_names), output_dir, elapsed,
    )
    eprint(msg)
