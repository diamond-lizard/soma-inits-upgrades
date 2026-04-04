"""Tier 2 task execution loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def _run_tier2_loop(ctx: EntryContext, needs_rerun: bool) -> bool:
    """Execute Tier 2 tasks for the entry. Returns updated needs_rerun."""
    from soma_inits_upgrades.processing import (
        TIER_2_HANDLERS,
        find_next_tier2_task,
    )
    from soma_inits_upgrades.processing_helpers import (
        check_progress,
        set_entry_error,
    )
    while True:
        status = ctx.entry_state.status
        if status in ("done", "error"):
            break
        task_name = find_next_tier2_task(ctx.entry_state.tasks_completed)
        if task_name is None:
            break
        completed_before = sum(ctx.entry_state.tasks_completed.values())
        try:
            result = TIER_2_HANDLERS[task_name](ctx)
            needs_rerun = needs_rerun or result
        except Exception as exc:
            set_entry_error(
                ctx, f"internal error in task {task_name}: {exc}",
            )
            break
        if not check_progress(
            completed_before, ctx.entry_state.tasks_completed,
            ctx.entry_state.status,
        ):
            name = ctx.entry_state.init_file
            set_entry_error(
                ctx,
                f"internal error: no progress made processing {name}",
            )
            break
    return needs_rerun
