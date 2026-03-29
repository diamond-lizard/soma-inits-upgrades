"""Per-entry git tasks: clone, default branch, latest ref."""

from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import RepoContext

LOW_DISK_THRESHOLD_MB = 500


def task_clone(repo_ctx: RepoContext) -> bool:
    """Clone the repository for this entry."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("clone", False):
        return False
    from soma_inits_upgrades.git_ops import clone_repo
    from soma_inits_upgrades.processing_helpers_repo import set_repo_error
    from soma_inits_upgrades.state import mark_repo_task_complete
    ctx = repo_ctx.entry_ctx
    avail_mb = shutil.disk_usage(str(ctx.output_dir)).free // (1024 * 1024)
    if avail_mb < LOW_DISK_THRESHOLD_MB:
        msg = f"Warning: low disk space ({avail_mb}MB available). Clone may fail."
        print(msg, file=sys.stderr)
    idx, total = ctx.entry_idx, ctx.total
    name = ctx.entry_state.init_file
    url = repo_ctx.repo_state.repo_url
    print(f"[{idx}/{total}] {name}: cloning {url}...", file=sys.stderr)
    success, error_msg = clone_repo(
        repo_ctx.repo_state.repo_url, repo_ctx.clone_dir,
        ctx.output_dir, run_fn=ctx.run_fn,
    )
    if not success:
        set_repo_error(repo_ctx, f"clone failed: {error_msg}")
        return False
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state, "clone", ctx.entry_state_path,
    )
    return False


def task_default_branch(repo_ctx: RepoContext) -> bool:
    """Detect the default branch of the cloned repository."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("default_branch", False):
        return False
    from soma_inits_upgrades.entry_tasks_diff import _cleanup_repo_temp
    from soma_inits_upgrades.git_ref_ops import detect_default_branch
    from soma_inits_upgrades.processing_helpers_repo import self_heal_repo_resource, set_repo_error
    from soma_inits_upgrades.state import mark_repo_task_complete
    ctx = repo_ctx.entry_ctx
    if self_heal_repo_resource(repo_ctx.clone_dir, "clone", repo_ctx):
        return False
    branch = detect_default_branch(repo_ctx.clone_dir, run_fn=ctx.run_fn)
    if branch is None:
        set_repo_error(repo_ctx, "could not detect default branch")
        _cleanup_repo_temp(repo_ctx)
        return False
    repo_ctx.repo_state.default_branch = branch
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state,
        "default_branch", ctx.entry_state_path,
    )
    return False
