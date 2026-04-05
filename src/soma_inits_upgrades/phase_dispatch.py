"""Phase dispatch lifecycle: viability checks and stage management."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint_error

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import UserInputFn
    from soma_inits_upgrades.state_schema import EntriesSummary, GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def check_processing_viability(
    entries_summary: EntriesSummary, entry_names: list[str], state_dir: Path,
) -> None:
    """Exit with code 1 if zero entries succeeded."""
    if entries_summary.done >= 1:
        return
    from soma_inits_upgrades.state import read_entry_state

    eprint_error("Error: no entries were successfully processed.")
    for name in entry_names:
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is not None and state.status == "error":
            eprint_error(f"  {state.init_file}: {state.notes or 'unknown error'}")
    sys.exit(1)


def handle_detected_changes(
    results: list[GroupedEntryDict], state_dir: Path, output_dir: Path,
    global_state: GlobalState, new_names: list[str],
    modified_names: list[str], orphan_count: int,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Handle new, modified, or orphaned entries. Returns True if changes found."""
    if not new_names and not modified_names and orphan_count == 0:
        return False
    from soma_inits_upgrades.entry_retry import (
        reset_phases_for_new_entries,
        retry_errored_entries,
    )
    from soma_inits_upgrades.graph import read_graph, write_graph
    from soma_inits_upgrades.graph_entry import remove_entries
    from soma_inits_upgrades.state import atomic_write_json, reconcile_entries_summary

    if modified_names:
        graph_path = output_dir / "soma-inits-dependency-graphs.json"
        graph, _ = read_graph(graph_path)
        remove_entries(graph, modified_names)
        write_graph(graph_path, graph)
    reset_phases_for_new_entries(global_state, new_names)
    retry_errored_entries(results, state_dir, input_fn=input_fn)
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    atomic_write_json(state_dir / "global.json", global_state)
    return True


def handle_retryable_errors(
    results: list[GroupedEntryDict], state_dir: Path, global_state: GlobalState,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Retry errored entries if any have remaining retries. Returns True if retried."""
    from soma_inits_upgrades.state import read_entry_state

    has_retryable = any(
        (s := read_entry_state(state_dir / f"{e['init_file']}.json")) is not None
        and s.status == "error"
        for e in results
    )
    if not has_retryable:
        return False
    from soma_inits_upgrades.entry_retry import retry_errored_entries
    from soma_inits_upgrades.state import reconcile_entries_summary
    from soma_inits_upgrades.state_lifecycle import reset_downstream_phases

    reset_downstream_phases(global_state)
    global_state.phases.entry_processing = "in_progress"
    retry_errored_entries(results, state_dir, input_fn=input_fn)
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    return True

