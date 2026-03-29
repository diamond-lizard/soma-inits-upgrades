"""Per-entry diff and cleanup tasks."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext, RepoContext


def task_diff(repo_ctx: RepoContext) -> bool:
    """Generate the diff between pinned and latest refs."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("diff", False):
        return False
    from soma_inits_upgrades.git_cleanup import generate_diff
    from soma_inits_upgrades.processing_helpers_repo import (
        self_heal_repo_resource,
        set_repo_done_early,
        set_repo_error,
    )
    from soma_inits_upgrades.state import mark_repo_task_complete
    ctx = repo_ctx.entry_ctx
    if self_heal_repo_resource(repo_ctx.clone_dir, "clone", repo_ctx):
        return False
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    print(f"{label} {ctx.entry_state.init_file}: generating diff...", file=sys.stderr)
    diff_path = repo_ctx.temp_dir / f"{ctx.init_stem}.diff"
    try:
        has_diff = generate_diff(
            repo_ctx.clone_dir, repo_ctx.repo_state.pinned_ref,
            repo_ctx.repo_state.latest_ref or "",
            diff_path, run_fn=ctx.run_fn,
        )
    except Exception as exc:
        set_repo_error(repo_ctx, f"diff generation failed: {exc}")
        _cleanup_repo_temp(repo_ctx)
        return False
    if not has_diff:
        msg = "empty diff - no changes between pinned and latest ref"
        set_repo_done_early(repo_ctx, "empty_diff", msg)
        _cleanup_repo_temp(repo_ctx)
        return False
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state, "diff", ctx.entry_state_path,
    )
    return False


def task_cleanup(ctx: EntryContext) -> bool:
    """Clean up temporary files for this entry."""
    if ctx.entry_state.tasks_completed.get("cleanup", False):
        return False
    from soma_inits_upgrades.state import mark_task_complete
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts

    delete_entry_artifacts(
        ctx.entry_state.init_file, ctx.output_dir,
        include_permanent=False, include_temp=True,
    )
    mark_task_complete(ctx.entry_state, "cleanup", ctx.entry_state_path)
    return False


def _cleanup_repo_temp(repo_ctx: RepoContext) -> None:
    """Delete temp artifacts on error or early exit (per-repo)."""
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts
    ctx = repo_ctx.entry_ctx
    delete_entry_artifacts(
        ctx.entry_state.init_file, ctx.output_dir,
        include_permanent=False, include_temp=True,
    )


def resolve_latest_ref(ctx: EntryContext) -> str | None:
    """Resolve the latest commit SHA on the default branch."""
    from soma_inits_upgrades.git_ref_ops import rev_parse
    clone_dir = ctx.tmp_dir / ctx.init_stem
    branch = ctx.entry_state.repos[0].default_branch
    return rev_parse(clone_dir, f"origin/{branch}", run_fn=ctx.run_fn)


def is_pin_current(pinned_ref: str, latest_ref: str) -> bool:
    """Return True if pinned ref equals latest ref."""
    return pinned_ref == latest_ref


def verify_pinned_ref(ctx: EntryContext) -> bool:
    """Verify the pinned ref exists in the repository."""
    from soma_inits_upgrades.git_ref_ops import verify_ref
    clone_dir = ctx.tmp_dir / ctx.init_stem
    return verify_ref(clone_dir, ctx.entry_state.repos[0].pinned_ref, run_fn=ctx.run_fn)
