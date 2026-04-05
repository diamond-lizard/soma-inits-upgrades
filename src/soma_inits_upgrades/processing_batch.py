"""Batch processing: cleanup orphaned files and iterate all entries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner, UserInputFn
    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def cleanup_orphaned_temp_files(
    results: list[GroupedEntryDict], state_dir: Path, output_dir: Path,
) -> None:
    """Reclaim orphaned temp files from prior interrupted runs."""
    from soma_inits_upgrades.state import atomic_write_json, read_entry_state
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts
    for entry in results:
        name = entry["init_file"]
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is None:
            continue
        cleanup_done = state.tasks_completed.get("temp_cleanup", False)
        is_terminal = state.status == "done" or (
            state.status == "error" and state.retries_remaining == 0
        )
        if not cleanup_done and is_terminal:
            delete_entry_artifacts(name, output_dir, include_permanent=False, include_temp=True)
            state.tasks_completed["temp_cleanup"] = True
            atomic_write_json(path, state)


def process_all_entries(
    results: list[GroupedEntryDict], state_dir: Path, output_dir: Path,
    global_state: GlobalState, run_fn: SubprocessRunner,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Iterate all entries and process each. Returns needs_rerun."""
    from soma_inits_upgrades.clipboard import make_xclip_checker
    from soma_inits_upgrades.processing import _validate_handlers
    from soma_inits_upgrades.processing_entry import process_single_entry
    _validate_handlers()
    xclip_checker = make_xclip_checker()
    cleanup_orphaned_temp_files(results, state_dir, output_dir)
    global_state_path = state_dir / "global.json"
    total = len(results)
    needs_rerun = False
    for idx, entry in enumerate(results, 1):
        name = entry['init_file']
        n_repos = len(entry['repos'])
        if idx > 1:
            eprint("-" * 72)
        eprint(
            f"[{idx}/{total}] Processing {name}"
            f" ({n_repos} repo(s))...",
        )
        result = process_single_entry(
            entry, idx, total, state_dir, output_dir,
            global_state, global_state_path, run_fn, results,
            xclip_checker, input_fn=input_fn,
        )
        needs_rerun = needs_rerun or result
    return needs_rerun
