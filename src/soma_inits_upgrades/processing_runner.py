"""Two-tier entry task runner loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks_diff import task_cleanup

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def run_entry_task_loop(ctx: EntryContext) -> bool:
    """Execute the two-tier entry task loop. Returns needs_rerun."""
    from soma_inits_upgrades.processing import (
        TIER_1_HANDLERS,
        find_next_tier1_task,
    )
    from soma_inits_upgrades.processing_helpers import check_progress
    from soma_inits_upgrades.processing_helpers_repo import set_repo_error
    from soma_inits_upgrades.protocols import RepoContext
    needs_rerun = False
    for repo_state in ctx.entry_state.repos:
        if repo_state.done_reason is not None:
            continue
        repo_ctx = RepoContext(
            entry_ctx=ctx, repo_state=repo_state,
            temp_dir=ctx.tmp_dir,
            clone_dir=ctx.tmp_dir / ctx.init_stem,
        )
        while True:
            task_name = find_next_tier1_task(repo_state.tier1_tasks_completed)
            if task_name is None:
                break
            completed_before = sum(repo_state.tier1_tasks_completed.values())
            try:
                result = TIER_1_HANDLERS[task_name](repo_ctx)
                needs_rerun = needs_rerun or result
            except Exception as exc:
                set_repo_error(
                    repo_ctx, f"internal error in task {task_name}: {exc}",
                )
                break
            if repo_state.done_reason is not None:
                break
            if not check_progress(
                completed_before, repo_state.tier1_tasks_completed,
                ctx.entry_state.status,
            ):
                url = repo_state.repo_url
                set_repo_error(
                    repo_ctx,
                    f"internal error: no progress made processing {url}",
                )
                break
    if any(r.done_reason is None for r in ctx.entry_state.repos):
        needs_rerun = _run_tier2_loop(ctx, needs_rerun)
    task_cleanup(ctx)
    return needs_rerun


def _run_tier2_loop(ctx: EntryContext, needs_rerun: bool) -> bool:
    """Execute Tier 2 tasks for the entry. Returns updated needs_rerun."""
    from soma_inits_upgrades.processing import (
        TIER_2_HANDLERS,
        find_next_tier2_task,
    )
    from soma_inits_upgrades.processing_helpers import check_progress, set_entry_error
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
            set_entry_error(ctx, f"internal error in task {task_name}: {exc}")
            break
        if not check_progress(
            completed_before, ctx.entry_state.tasks_completed,
            ctx.entry_state.status,
        ):
            name = ctx.entry_state.init_file
            set_entry_error(
                ctx, f"internal error: no progress made processing {name}",
            )
            break
    return needs_rerun
