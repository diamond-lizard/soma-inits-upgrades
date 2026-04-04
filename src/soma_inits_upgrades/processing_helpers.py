"""Processing helpers: error/done status, progress guard, self-healing."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext

SELF_HEALING_LIMIT = 5


def set_entry_error(ctx: EntryContext, message: str) -> None:
    """Centralize error bookkeeping for a per-entry task failure."""
    from soma_inits_upgrades.state import atomic_write_json

    ctx.entry_state.status = "error"
    ctx.entry_state.notes = message
    ctx.global_state.entries_summary.in_progress -= 1
    ctx.global_state.entries_summary.error += 1
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    atomic_write_json(ctx.global_state_path, ctx.global_state)
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    print(f"{label} {ctx.entry_state.init_file}: error: {message}", file=sys.stderr)


def set_entry_done_early(
    ctx: EntryContext, done_reason: str, notes: str,
) -> None:
    """Centralize early-completion bookkeeping for a per-entry task."""
    from soma_inits_upgrades.state import atomic_write_json

    ctx.entry_state.status = "done"
    ctx.entry_state.done_reason = done_reason
    ctx.entry_state.notes = notes
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)


def check_progress(
    completed_before: int, entry_state_tasks: dict[str, bool], status: str,
) -> bool:
    """Return True if progress was made (task completed, reset, or status changed)."""
    completed_after = sum(entry_state_tasks.values())
    if completed_after > completed_before:
        return True
    if completed_after < completed_before:
        return True
    return status in ("done", "error")


def self_heal_entry_resource(
    resource_path: Path, creating_task: str, ctx: EntryContext,
) -> bool:
    """Check if a Tier 2 resource exists; reset its entry task if missing.

    Returns True if a reset was triggered (caller should return early).
    Returns False if the resource exists (proceed normally).
    """
    if resource_path.exists():
        return False
    if not ctx.entry_state.tasks_completed.get(creating_task, False):
        return False
    ctx.entry_state.tasks_completed[creating_task] = False
    count = ctx.reset_counters.get(creating_task, 0) + 1
    ctx.reset_counters[creating_task] = count
    if count >= SELF_HEALING_LIMIT:
        set_entry_error(
            ctx, f"self-healing limit exceeded: {resource_path.name} missing "
            f"{count} times for {ctx.entry_state.init_file}",
        )
        print(
            f"FATAL: {resource_path.name} could not be regenerated "
            f"for {ctx.entry_state.init_file} after "
            f"{count} attempts. Fix the underlying issue "
            f"(network, permissions, upstream repo) and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)
    name = ctx.entry_state.init_file
    print(
        f"Warning: {resource_path.name} missing, re-executing {creating_task} "
        f"for {name} (attempt {count}/{SELF_HEALING_LIMIT})",
        file=sys.stderr,
    )
    return True


self_heal_resource = self_heal_entry_resource  # Backward compat
