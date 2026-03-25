"""Per-Entry Processing stage: entry loop, task dispatch, TASK_HANDLERS dict."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks import (
    task_cleanup,
    task_clone,
    task_default_branch,
    task_diff,
    task_latest_ref,
)
from soma_inits_upgrades.entry_tasks_analysis import (
    task_deps,
    task_graph_update,
    task_security_review,
    task_symbols,
    task_upgrade_analysis,
    task_upgrade_report,
    task_version_check,
)
from soma_inits_upgrades.output_validation import task_validate_outputs
from soma_inits_upgrades.protocols import EntryContext, TaskHandler
from soma_inits_upgrades.state_schema import TASK_ORDER

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner, UserInputFn, XclipChecker
    from soma_inits_upgrades.state_schema import EntryState, GlobalState

TASK_HANDLERS: dict[str, TaskHandler] = {
    "clone": task_clone,
    "default_branch": task_default_branch,
    "latest_ref": task_latest_ref,
    "diff": task_diff,
    "deps": task_deps,
    "version_check": task_version_check,
    "security_review": task_security_review,
    "symbols": task_symbols,
    "upgrade_analysis": task_upgrade_analysis,
    "upgrade_report": task_upgrade_report,
    "graph_update": task_graph_update,
    "validate_outputs": task_validate_outputs,
    "cleanup": task_cleanup,
}


def find_next_task(tasks_completed: dict[str, bool]) -> str | None:
    """Return the first incomplete task name, or None if all done."""
    for task in TASK_ORDER:
        if not tasks_completed.get(task, False):
            return task
    return None


def run_entry_task_loop(ctx: EntryContext) -> bool:
    """Execute the per-entry task while-loop. Returns needs_rerun."""
    from soma_inits_upgrades.processing_helpers import check_progress, set_entry_error

    needs_rerun = False
    while True:
        status = ctx.entry_state.status
        if status in ("done", "error"):
            break
        task_name = find_next_task(ctx.entry_state.tasks_completed)
        if task_name is None:
            break
        completed_before = sum(ctx.entry_state.tasks_completed.values())
        try:
            result = TASK_HANDLERS[task_name](ctx)
            needs_rerun = needs_rerun or result
        except Exception as exc:
            set_entry_error(ctx, f"internal error in task {task_name}: {exc}")
            break
        if not check_progress(
            completed_before, ctx.entry_state.tasks_completed,
            ctx.entry_state.status,
        ):
            name = ctx.entry_state.init_file
            set_entry_error(ctx, f"internal error: no progress made processing {name}")
            break
    return needs_rerun


def cleanup_orphaned_temp_files(
    results: list[dict[str, str]], state_dir: Path, output_dir: Path,
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
        cleanup_done = state.tasks_completed.get("cleanup", False)
        is_terminal = state.status == "done" or (
            state.status == "error" and state.retries_remaining == 0
        )
        if not cleanup_done and is_terminal:
            delete_entry_artifacts(name, output_dir, include_permanent=False, include_temp=True)
            state.tasks_completed["cleanup"] = True
            atomic_write_json(path, state)


def ensure_entry_state(
    entry: dict[str, str], state_dir: Path, global_state: GlobalState,
) -> EntryState | None:
    """Load or create per-entry state. Returns EntryState or None on error."""
    from soma_inits_upgrades.state import atomic_write_json, read_entry_state
    from soma_inits_upgrades.state_schema import EntryState

    path = state_dir / f"{entry['init_file']}.json"
    state = read_entry_state(path)
    if state is None:
        name = entry["init_file"]
        print(f"Warning: state file missing for {name}, creating default", file=sys.stderr)
        state = EntryState(
            init_file=entry["init_file"],
            repo_url=entry["repo_url"],
            pinned_ref=entry["pinned_ref"],
        )
        atomic_write_json(path, state)
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
    entry: dict[str, str], idx: int, total: int,
    state_dir: Path, output_dir: Path,
    global_state: GlobalState, global_state_path: Path,
    run_fn: SubprocessRunner, results: list[dict[str, str]],
    xclip_checker: XclipChecker, input_fn: UserInputFn | None = None,
) -> bool:
    """Process a single entry. Returns needs_rerun."""
    from soma_inits_upgrades.processing_helpers import finalize_entry

    state = ensure_entry_state(entry, state_dir, global_state)
    if state is None:
        return False
    entry_state_path = state_dir / f"{entry['init_file']}.json"
    if not initialize_entry(state, entry_state_path, global_state, global_state_path):
        return False
    init_stem = entry["init_file"].removesuffix(".el")
    ctx = EntryContext(
        entry_state=state,
        entry_state_path=entry_state_path,
        global_state=global_state,
        global_state_path=global_state_path,
        entry_idx=idx,
        total=total,
        output_dir=output_dir,
        tmp_dir=output_dir / ".tmp",
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


def _validate_handlers() -> None:
    """Validate TASK_HANDLERS keys match TASK_ORDER."""
    handler_keys = set(TASK_HANDLERS.keys())
    order_keys = set(TASK_ORDER)
    if handler_keys != order_keys:
        missing = order_keys - handler_keys
        extra = handler_keys - order_keys
        raise ValueError(f"Missing handlers: {missing}; Extra handlers: {extra}")


def process_all_entries(
    results: list[dict[str, str]], state_dir: Path, output_dir: Path,
    global_state: GlobalState, run_fn: SubprocessRunner,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Iterate all entries and process each. Returns needs_rerun."""
    from soma_inits_upgrades.clipboard import make_xclip_checker

    _validate_handlers()
    xclip_checker = make_xclip_checker()
    cleanup_orphaned_temp_files(results, state_dir, output_dir)
    global_state_path = state_dir / "global.json"
    total = len(results)
    needs_rerun = False
    for idx, entry in enumerate(results, 1):
        print(f"[{idx}/{total}] Processing {entry['init_file']}...", file=sys.stderr)
        result = process_single_entry(
            entry, idx, total, state_dir, output_dir,
            global_state, global_state_path, run_fn, results,
            xclip_checker, input_fn=input_fn,
        )
        needs_rerun = needs_rerun or result
    return needs_rerun
