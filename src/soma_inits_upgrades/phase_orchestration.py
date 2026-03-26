"""Phase orchestration: setup and top-level phase dispatch sequence."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner
    from soma_inits_upgrades.state_schema import GlobalState


def run_setup(
    global_state: GlobalState | None,
    global_state_path: Path,
    resolved_stale: Path,
    resolved_output: Path,
    state_dir: Path,
    results: list[dict[str, str]],
) -> GlobalState:
    """Execute the Setup stage and return the updated global state."""
    from soma_inits_upgrades.setup_completion import (
        complete_setup,
        initialize_dep_graph,
        initialize_entry_states,
    )
    from soma_inits_upgrades.setup_stage import (
        create_tmp_directory,
        initialize_global_state,
        prompt_emacs_version,
    )

    graph_path = resolved_output / "soma-inits-dependency-graphs.json"
    gs = initialize_global_state(global_state, global_state_path, resolved_stale)
    prompt_emacs_version(gs, global_state_path)
    create_tmp_directory(resolved_output)
    initialize_entry_states(results, state_dir, resolved_output, gs)
    initialize_dep_graph(graph_path)
    complete_setup(gs, global_state_path, results)
    return gs


def run_all_phases(
    global_state: GlobalState | None,
    global_state_path: Path,
    resolved_stale: Path,
    resolved_output: Path,
    state_dir: Path,
    results: list[dict[str, str]],
    run_fn: SubprocessRunner,
) -> None:
    """Execute all four phases in order, resuming from where left off."""
    from soma_inits_upgrades.finalization import (
        dispatch_graph_finalization,
        dispatch_summary_stage,
    )
    from soma_inits_upgrades.phase_dispatch import check_processing_viability
    from soma_inits_upgrades.phase_dispatch_run import dispatch_entry_processing
    from soma_inits_upgrades.state import read_global_state

    start_time = time.monotonic()

    if global_state is None or global_state.phases.setup != "done":
        gs = run_setup(
            global_state, global_state_path,
            resolved_stale, resolved_output, state_dir, results,
        )
    else:
        gs = global_state

    dispatch_entry_processing(results, state_dir, resolved_output, gs, run_fn)
    gs = read_global_state(global_state_path) or gs
    check_processing_viability(gs.entries_summary, gs.entry_names, state_dir)
    dispatch_graph_finalization(gs, global_state_path, resolved_output)
    dispatch_summary_stage(gs, global_state_path, resolved_output, start_time)
