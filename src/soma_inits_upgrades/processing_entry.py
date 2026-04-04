"""Processing entry: per-entry initialization, processing, and batch iteration."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner, UserInputFn, XclipChecker
    from soma_inits_upgrades.state_schema import EntryState, GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def ensure_entry_state(
    entry: GroupedEntryDict, state_dir: Path, global_state: GlobalState,
) -> EntryState | None:
    """Load or create per-entry state. Returns EntryState or None on error."""
    from soma_inits_upgrades.state import atomic_write_json, read_entry_state
    from soma_inits_upgrades.state_schema import EntryState, RepoState
    path = state_dir / f"{entry['init_file']}.json"
    state = read_entry_state(path)
    if state is None:
        name = entry["init_file"]
        print(f"Warning: state file missing for {name}, creating default", file=sys.stderr)
        state = EntryState(
            init_file=entry["init_file"],
            repos=[
                RepoState(repo_url=r["repo_url"], pinned_ref=r["pinned_ref"])
                for r in entry["repos"]
            ],
        )
        atomic_write_json(path, state)
        if name not in global_state.entry_names:
            global_state.entries_summary.total += 1
            global_state.entries_summary.pending += 1
    return state


def initialize_entry(
    state: EntryState, entry_state_path: Path,
    global_state: GlobalState, global_state_path: Path,
) -> bool:
    """Handle status transitions. Returns True to proceed, False to skip."""
    from soma_inits_upgrades.state import atomic_write_json
    if state.status in ("done", "error"):
        return False
    if state.status == "pending":
        state.status = "in_progress"
        global_state.entries_summary.pending -= 1
        global_state.entries_summary.in_progress += 1
        global_state.current_entry = state.init_file
        atomic_write_json(entry_state_path, state)
        atomic_write_json(global_state_path, global_state)
    else:
        global_state.current_entry = state.init_file
    return True


def process_single_entry(
    entry: GroupedEntryDict, idx: int, total: int,
    state_dir: Path, output_dir: Path,
    global_state: GlobalState, global_state_path: Path,
    run_fn: SubprocessRunner, results: list[GroupedEntryDict],
    xclip_checker: XclipChecker, input_fn: UserInputFn | None = None,
) -> bool:
    """Process a single entry. Returns needs_rerun."""
    from soma_inits_upgrades.processing import run_entry_task_loop
    from soma_inits_upgrades.processing_finalize import finalize_entry
    state = ensure_entry_state(entry, state_dir, global_state)
    if state is None:
        return False
    entry_state_path = state_dir / f"{entry['init_file']}.json"
    if not initialize_entry(state, entry_state_path, global_state, global_state_path):
        return False
    from soma_inits_upgrades.protocols import EntryContext
    init_stem = entry["init_file"].removesuffix(".el")
    ctx = EntryContext(
        entry_state=state,
        entry_state_path=entry_state_path,
        global_state=global_state,
        global_state_path=global_state_path,
        entry_idx=idx,
        total=total,
        output_dir=output_dir,
        tmp_dir=output_dir / ".tmp" / init_stem,
        state_dir=state_dir,
        init_stem=init_stem,
        results=results,
        xclip_checker=xclip_checker,
        run_fn=run_fn,
        input_fn=input_fn,
    )
    needs_rerun = run_entry_task_loop(ctx)
    finalize_entry(ctx)
    return needs_rerun
