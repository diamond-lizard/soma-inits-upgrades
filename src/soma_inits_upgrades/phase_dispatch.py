"""Phase dispatch lifecycle: viability checks and stage management."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner, UserInputFn
    from soma_inits_upgrades.state_schema import EntriesSummary, GlobalState


def check_processing_viability(
    entries_summary: EntriesSummary, entry_names: list[str], state_dir: Path,
) -> None:
    """Exit with code 1 if zero entries succeeded."""
    if entries_summary.done >= 1:
        return
    from soma_inits_upgrades.state import read_entry_state

    print("Error: no entries were successfully processed.", file=sys.stderr)
    for name in entry_names:
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is not None and state.status == "error":
            print(f"  {state.init_file}: {state.notes or 'unknown error'}", file=sys.stderr)
    sys.exit(1)


def handle_detected_changes(
    results: list[dict[str, str]], state_dir: Path, output_dir: Path,
    global_state: GlobalState, new_names: list[str],
    modified_names: list[str], orphan_count: int,
) -> bool:
    """Handle new, modified, or orphaned entries. Returns True if changes found."""
    if not new_names and not modified_names and orphan_count == 0:
        return False
    from soma_inits_upgrades.entry_changes import (
        reset_phases_for_new_entries,
        retry_errored_entries,
    )
    from soma_inits_upgrades.graph import read_graph, remove_entries, write_graph
    from soma_inits_upgrades.state import atomic_write_json, reconcile_entries_summary

    if modified_names:
        graph_path = output_dir / "soma-inits-dependency-graphs.json"
        graph, _ = read_graph(graph_path)
        remove_entries(graph, modified_names)
        write_graph(graph_path, graph)
    reset_phases_for_new_entries(global_state, new_names)
    retry_errored_entries(results, state_dir)
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    atomic_write_json(state_dir / "global.json", global_state)
    return True


def handle_retryable_errors(
    results: list[dict[str, str]], state_dir: Path, global_state: GlobalState,
) -> bool:
    """Retry errored entries if any have remaining retries. Returns True if retried."""
    from soma_inits_upgrades.state import read_entry_state

    has_retryable = any(
        (s := read_entry_state(state_dir / f"{e['init_file']}.json")) is not None
        and s.status == "error" and s.retries_remaining > 0
        for e in results
    )
    if not has_retryable:
        return False
    from soma_inits_upgrades.entry_changes import retry_errored_entries
    from soma_inits_upgrades.state import reconcile_entries_summary, reset_downstream_phases

    reset_downstream_phases(global_state)
    global_state.phases.entry_processing = "in_progress"
    retry_errored_entries(results, state_dir)
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    return True


def resume_completed_entry_processing(
    results: list[dict[str, str]], state_dir: Path,
    output_dir: Path, global_state: GlobalState,
) -> bool:
    """Handle entry_processing already done. Returns True to reprocess."""
    from soma_inits_upgrades.entry_changes import detect_new_or_modified_entries
    from soma_inits_upgrades.state import atomic_write_json

    new, modified, orphan_count = detect_new_or_modified_entries(
        results, state_dir, output_dir, global_state,
    )
    atomic_write_json(state_dir / "global.json", global_state)
    if handle_detected_changes(
        results, state_dir, output_dir, global_state, new, modified, orphan_count,
    ):
        return True
    return handle_retryable_errors(results, state_dir, global_state)


def run_entry_processing(
    results: list[dict[str, str]], state_dir: Path, output_dir: Path,
    global_state: GlobalState, run_fn: SubprocessRunner,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Run entry processing when not yet done. Returns needs_rerun."""
    from soma_inits_upgrades.entry_changes import (
        detect_new_or_modified_entries,
        retry_errored_entries,
    )
    from soma_inits_upgrades.state import atomic_write_json, reconcile_entries_summary

    global_state.phases.entry_processing = "in_progress"
    detect_new_or_modified_entries(results, state_dir, output_dir, global_state)
    global_state.entry_names = [e["init_file"] for e in results]
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    atomic_write_json(state_dir / "global.json", global_state)
    retry_errored_entries(results, state_dir)
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    from soma_inits_upgrades.processing import process_all_entries

    return process_all_entries(
        results, state_dir, output_dir, global_state, run_fn, input_fn=input_fn,
    )


def complete_entry_processing(
    global_state: GlobalState, state_dir: Path, needs_rerun: bool,
) -> None:
    """Set entry_processing phase status after all entries processed."""
    from soma_inits_upgrades.state import atomic_write_json, reconcile_entries_summary

    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    if needs_rerun:
        global_state.phases.entry_processing = "in_progress"
    else:
        global_state.phases.entry_processing = "done"
    atomic_write_json(state_dir / "global.json", global_state)


def dispatch_entry_processing(
    results: list[dict[str, str]], state_dir: Path, output_dir: Path,
    global_state: GlobalState, run_fn: SubprocessRunner,
    input_fn: UserInputFn | None = None,
) -> None:
    """Orchestrate entry processing: resume or run, then complete."""
    from soma_inits_upgrades.processing import process_all_entries

    if global_state.phases.entry_processing == "done":
        if not resume_completed_entry_processing(
            results, state_dir, output_dir, global_state,
        ):
            return
        needs_rerun = process_all_entries(
            results, state_dir, output_dir, global_state, run_fn, input_fn=input_fn,
        )
    else:
        needs_rerun = run_entry_processing(
            results, state_dir, output_dir, global_state, run_fn, input_fn=input_fn,
        )
    complete_entry_processing(global_state, state_dir, needs_rerun)
