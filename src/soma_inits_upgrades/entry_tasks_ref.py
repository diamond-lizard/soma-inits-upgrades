"""Per-entry git task: latest ref resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import RepoContext


def task_latest_ref(repo_ctx: RepoContext) -> bool:
    """Resolve latest ref and check if pin is current."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("latest_ref", False):
        return False
    from soma_inits_upgrades.entry_tasks_diff import (
        _cleanup_repo_temp,
        is_pin_current,
        resolve_latest_ref,
        verify_pinned_ref,
    )
    from soma_inits_upgrades.processing_helpers_repo import (
        self_heal_repo_resource,
        set_repo_done_early,
        set_repo_error,
    )
    from soma_inits_upgrades.state import mark_repo_task_complete
    ctx = repo_ctx.entry_ctx
    if self_heal_repo_resource(repo_ctx.clone_dir, "clone", repo_ctx):
        return False
    latest = resolve_latest_ref(ctx)
    if latest is None:
        branch = repo_ctx.repo_state.default_branch
        set_repo_error(repo_ctx, f"could not resolve latest ref on branch {branch}")
        _cleanup_repo_temp(repo_ctx)
        return False
    repo_ctx.repo_state.latest_ref = latest
    if is_pin_current(repo_ctx.repo_state.pinned_ref, latest):
        msg = "pinned ref is already at latest commit - no upgrade needed"
        set_repo_done_early(repo_ctx, "already_latest", msg)
        _cleanup_repo_temp(repo_ctx)
        return False
    if not verify_pinned_ref(ctx):
        pin = repo_ctx.repo_state.pinned_ref
        set_repo_error(repo_ctx, f"pinned ref {pin} does not exist in repository")
        _cleanup_repo_temp(repo_ctx)
        return False
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state,
        "latest_ref", ctx.entry_state_path,
    )
    return False
