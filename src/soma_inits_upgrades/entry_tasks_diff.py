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


def task_temp_cleanup(ctx: EntryContext) -> bool:
    """Delete remaining temp artifacts under the per-init-file directory."""
    if ctx.entry_state.tasks_completed.get("temp_cleanup", False):
        return False
    from soma_inits_upgrades.git_ops import safe_rmtree
    from soma_inits_upgrades.state import mark_task_complete
    if ctx.tmp_dir.is_dir():
        safe_rmtree(ctx.tmp_dir, ctx.output_dir)
    mark_task_complete(ctx.entry_state, "temp_cleanup", ctx.entry_state_path)
    return False


def _cleanup_repo_temp(repo_ctx: RepoContext) -> None:
    """Delete per-repo temp subdirectory on error or early exit."""
    from soma_inits_upgrades.git_ops import safe_rmtree
    if repo_ctx.temp_dir.is_dir():
        safe_rmtree(repo_ctx.temp_dir, repo_ctx.entry_ctx.output_dir)


def clone_cleanup(repo_ctx: RepoContext) -> None:
    """Delete the clone directory for a repo. Idempotent no-op if absent."""
    from soma_inits_upgrades.git_ops import safe_rmtree
    if repo_ctx.clone_dir.is_dir():
        safe_rmtree(repo_ctx.clone_dir, repo_ctx.entry_ctx.output_dir)

def resolve_latest_ref(repo_ctx: RepoContext) -> str | None:
    """Resolve the latest commit SHA on the default branch."""
    from soma_inits_upgrades.git_ref_ops import rev_parse
    branch = repo_ctx.repo_state.default_branch
    if branch is None:
        return None
    return rev_parse(
        repo_ctx.clone_dir, branch,
        run_fn=repo_ctx.entry_ctx.run_fn,
    )


def is_pin_current(pinned_ref: str, latest_ref: str) -> bool:
    """Return True if pinned ref equals latest ref."""
    return pinned_ref == latest_ref


def verify_pinned_ref(repo_ctx: RepoContext) -> bool:
    """Verify the pinned ref exists in the repository."""
    from soma_inits_upgrades.git_ref_ops import verify_ref
    return verify_ref(
        repo_ctx.clone_dir, repo_ctx.repo_state.pinned_ref,
        run_fn=repo_ctx.entry_ctx.run_fn,
    )
