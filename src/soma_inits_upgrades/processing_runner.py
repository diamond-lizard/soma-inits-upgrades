"""Two-tier entry task runner loop."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks_diff import clone_cleanup, task_temp_cleanup
from soma_inits_upgrades.processing_tier1 import _run_tier1_tasks
from soma_inits_upgrades.processing_tier2 import _run_tier2_loop
from soma_inits_upgrades.repo_utils import derive_repo_dir_name
from soma_inits_upgrades.state import atomic_write_json

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state_schema import EntryState, RepoState


def _validate_repo_artifacts(
    repo_state: RepoState,
    temp_dir: Path,
    entry_state: EntryState,
    entry_state_path: Path,
) -> None:
    """Reset Tier 1 tasks when temp dir missing but all are done."""
    all_done = all(repo_state.tier1_tasks_completed.values())
    if not all_done or temp_dir.is_dir():
        return
    for key in repo_state.tier1_tasks_completed:
        repo_state.tier1_tasks_completed[key] = False
    repo_state.package_name = None
    atomic_write_json(entry_state_path, entry_state)
    print(
        f"Self-heal: reset Tier 1 tasks for {repo_state.repo_url}"
        " (temp directory missing)",
        file=sys.stderr,
    )


def _reset_tier1_on_restart(ctx: EntryContext) -> None:
    """Reset Tier 1 tasks on restart when security_review incomplete."""
    if ctx.entry_state.tasks_completed.get("security_review", False):
        return
    any_reset = False
    for repo_state in ctx.entry_state.repos:
        if repo_state.done_reason is not None:
            continue
        if not all(repo_state.tier1_tasks_completed.values()):
            continue
        for key in repo_state.tier1_tasks_completed:
            repo_state.tier1_tasks_completed[key] = False
        repo_state.package_name = None
        any_reset = True
        print(
            f"Restart detected: resetting Tier 1 tasks"
            f" for {repo_state.repo_url}",
            file=sys.stderr,
        )
    if any_reset:
        atomic_write_json(ctx.entry_state_path, ctx.entry_state)


def run_entry_task_loop(ctx: EntryContext) -> bool:
    """Execute the two-tier entry task loop. Returns needs_rerun."""
    from soma_inits_upgrades.protocols import RepoContext
    needs_rerun = False
    _reset_tier1_on_restart(ctx)
    for repo_state in ctx.entry_state.repos:
        if repo_state.done_reason is not None:
            continue
        repo_temp = ctx.tmp_dir / derive_repo_dir_name(repo_state.repo_url)
        repo_ctx = RepoContext(
            entry_ctx=ctx, repo_state=repo_state,
            temp_dir=repo_temp,
            clone_dir=repo_temp / "clone",
        )
        _validate_repo_artifacts(
            repo_state, repo_temp,
            ctx.entry_state, ctx.entry_state_path,
        )
        needs_rerun = _run_tier1_tasks(
            repo_ctx, ctx, needs_rerun,
        )
        clone_cleanup(repo_ctx)
    if any(r.done_reason is None for r in ctx.entry_state.repos):
        needs_rerun = _run_tier2_loop(ctx, needs_rerun)
    task_temp_cleanup(ctx)
    return needs_rerun
