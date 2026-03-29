"""Phase dispatch runners: entry processing execution and completion."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner, UserInputFn
    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def run_entry_processing(
    results: list[GroupedEntryDict], state_dir: Path, output_dir: Path,
    global_state: GlobalState, run_fn: SubprocessRunner,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Run entry processing when not yet done. Returns needs_rerun."""
    from soma_inits_upgrades.entry_retry import retry_errored_entries
    from soma_inits_upgrades.state import atomic_write_json, reconcile_entries_summary

    global_state.phases.entry_processing = "in_progress"
    from soma_inits_upgrades.entry_changes import detect_new_or_modified_entries
    detect_new_or_modified_entries(results, state_dir, output_dir, global_state)
    global_state.entry_names = [e["init_file"] for e in results]
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    atomic_write_json(state_dir / "global.json", global_state)
    retry_errored_entries(results, state_dir)
    global_state.entries_summary = reconcile_entries_summary(global_state.entry_names, state_dir)
    from soma_inits_upgrades.processing_batch import process_all_entries
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
    results: list[GroupedEntryDict], state_dir: Path, output_dir: Path,
    global_state: GlobalState, run_fn: SubprocessRunner,
    input_fn: UserInputFn | None = None,
) -> None:
    """Orchestrate entry processing: resume or run, then complete."""
    from soma_inits_upgrades.phase_dispatch import resume_completed_entry_processing
    from soma_inits_upgrades.processing_batch import process_all_entries
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
