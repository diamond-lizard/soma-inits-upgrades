"""Tier 1 task dispatch and execution loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext, RepoContext


def _dispatch_tier1_task(
    repo_ctx: RepoContext, task_name: str, status: str,
) -> tuple[bool, bool]:
    """Run one Tier 1 task. Returns (needs_rerun, should_break)."""
    from soma_inits_upgrades.processing import TIER_1_HANDLERS
    from soma_inits_upgrades.processing_helpers import check_progress
    from soma_inits_upgrades.processing_helpers_repo import set_repo_error
    rs = repo_ctx.repo_state
    completed_before = sum(rs.tier1_tasks_completed.values())
    try:
        result = TIER_1_HANDLERS[task_name](repo_ctx)
    except Exception as exc:
        set_repo_error(
            repo_ctx, f"internal error in task {task_name}: {exc}", exc,
        )
        return False, True
    if rs.done_reason is not None:
        return result, True
    if not check_progress(
        completed_before, rs.tier1_tasks_completed, status,
    ):
        set_repo_error(
            repo_ctx,
            f"internal error: no progress made processing {rs.repo_url}",
        )
        return False, True
    return result, False


def _run_tier1_tasks(
    repo_ctx: RepoContext,
    ctx: EntryContext,
    needs_rerun: bool,
) -> bool:
    """Dispatch Tier 1 tasks for one repo. Returns updated needs_rerun."""
    from soma_inits_upgrades.processing import find_next_tier1_task
    rs = repo_ctx.repo_state
    while True:
        task_name = find_next_tier1_task(rs.tier1_tasks_completed)
        if task_name is None:
            break
        result, should_break = _dispatch_tier1_task(
            repo_ctx, task_name, ctx.entry_state.status,
        )
        needs_rerun = needs_rerun or result
        if should_break:
            break
    return needs_rerun
