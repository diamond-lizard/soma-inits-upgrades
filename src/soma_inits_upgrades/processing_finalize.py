"""Processing finalization: entry completion bookkeeping and cleanup."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def finalize_entry(ctx: EntryContext) -> None:
    """Post-loop cleanup and bookkeeping for a completed entry."""
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts
    status = ctx.entry_state.status
    cleanup_done = ctx.entry_state.tasks_completed.get("cleanup", False)
    is_permanent_error = status == "error" and ctx.entry_state.retries_remaining == 0
    can_cleanup = status == "done" or is_permanent_error
    if not cleanup_done and can_cleanup:
        delete_entry_artifacts(
            ctx.entry_state.init_file, ctx.output_dir,
            include_permanent=False, include_temp=True,
        )
        ctx.entry_state.tasks_completed["cleanup"] = True
        if status == "error":
            _cleanup_malformed(ctx)
            atomic_write_json(ctx.entry_state_path, ctx.entry_state)
            return
    if status == "error" and ctx.entry_state.retries_remaining == 0:
        _cleanup_malformed(ctx)
    if status != "error":
        complete_entry_bookkeeping(ctx)


def _cleanup_malformed(ctx: EntryContext) -> None:
    """Remove .malformed files for a permanently-errored entry."""
    from soma_inits_upgrades.output_validation_tasks import cleanup_malformed_files
    cleanup_malformed_files(ctx.output_dir, ctx.entry_state.init_file)


def complete_entry_bookkeeping(ctx: EntryContext) -> None:
    """Update global state and write files for a done entry."""
    from soma_inits_upgrades.state import atomic_write_json
    ctx.entry_state.status = "done"
    ctx.global_state.entries_summary.in_progress -= 1
    ctx.global_state.entries_summary.done += 1
    ctx.global_state.current_entry = _next_pending_entry(ctx)
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    atomic_write_json(ctx.global_state_path, ctx.global_state)
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    print(f"{label} {ctx.entry_state.init_file}: done", file=sys.stderr)


def _next_pending_entry(ctx: EntryContext) -> str | None:
    """Return the next pending entry name, or None."""
    from soma_inits_upgrades.state import read_entry_state
    for name in ctx.global_state.entry_names:
        path = ctx.state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is not None and state.status in ("pending", "in_progress"):
            return name
    return None
