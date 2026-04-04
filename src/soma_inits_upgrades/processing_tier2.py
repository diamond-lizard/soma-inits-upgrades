"""Tier 2 task execution loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext



def _dispatch_tier2_task(
    ctx: EntryContext, task_name: str,
) -> tuple[bool, bool]:
    """Run one Tier 2 task. Returns (needs_rerun, should_break)."""
    from soma_inits_upgrades.processing import TIER_2_HANDLERS
    from soma_inits_upgrades.processing_helpers import (
        check_progress,
        set_entry_error,
    )
    completed_before = sum(ctx.entry_state.tasks_completed.values())
    try:
        result = TIER_2_HANDLERS[task_name](ctx)
    except Exception as exc:
        set_entry_error(
            ctx, f"internal error in task {task_name}: {exc}",
        )
        return False, True
    if not check_progress(
        completed_before, ctx.entry_state.tasks_completed,
        ctx.entry_state.status,
    ):
        name = ctx.entry_state.init_file
        set_entry_error(
            ctx,
            f"internal error: no progress made processing {name}",
        )
        return False, True
    return result, False

def _run_tier2_loop(ctx: EntryContext, needs_rerun: bool) -> bool:
    """Execute Tier 2 tasks for the entry. Returns updated needs_rerun."""
    from soma_inits_upgrades.processing import find_next_tier2_task
    while True:
        status = ctx.entry_state.status
        if status in ("done", "error"):
            break
        task_name = find_next_tier2_task(ctx.entry_state.tasks_completed)
        if task_name is None:
            break
        result, should_break = _dispatch_tier2_task(ctx, task_name)
        needs_rerun = needs_rerun or result
        if should_break:
            break
    return needs_rerun
