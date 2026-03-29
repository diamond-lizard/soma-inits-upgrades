"""Per-entry git tasks: clone, default branch, latest ref."""

from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext

LOW_DISK_THRESHOLD_MB = 500


def task_clone(ctx: EntryContext) -> bool:
    """Clone the repository for this entry."""
    if ctx.entry_state.tasks_completed.get("clone", False):
        return False
    from soma_inits_upgrades.git_ops import clone_repo
    from soma_inits_upgrades.processing_helpers import set_entry_error
    from soma_inits_upgrades.state import mark_task_complete
    avail_mb = shutil.disk_usage(str(ctx.output_dir)).free // (1024 * 1024)
    if avail_mb < LOW_DISK_THRESHOLD_MB:
        msg = f"Warning: low disk space ({avail_mb}MB available). Clone may fail."
        print(msg, file=sys.stderr)
    idx, total = ctx.entry_idx, ctx.total
    name = ctx.entry_state.init_file
    url = ctx.entry_state.repos[0].repo_url
    print(f"[{idx}/{total}] {name}: cloning {url}...", file=sys.stderr)
    clone_dir = ctx.tmp_dir / ctx.init_stem
    success, error_msg = clone_repo(
        ctx.entry_state.repos[0].repo_url, clone_dir, ctx.output_dir, run_fn=ctx.run_fn,
    )
    if not success:
        set_entry_error(ctx, f"clone failed: {error_msg}")
        return False
    mark_task_complete(ctx.entry_state, "clone", ctx.entry_state_path)
    return False


def task_default_branch(ctx: EntryContext) -> bool:
    """Detect the default branch of the cloned repository."""
    if ctx.entry_state.tasks_completed.get("default_branch", False):
        return False
    from soma_inits_upgrades.entry_tasks_diff import _cleanup_temp
    from soma_inits_upgrades.git_ref_ops import detect_default_branch
    from soma_inits_upgrades.processing_helpers import self_heal_resource, set_entry_error
    from soma_inits_upgrades.state import atomic_write_json
    clone_dir = ctx.tmp_dir / ctx.init_stem
    if self_heal_resource(clone_dir, "clone", ctx):
        return False
    branch = detect_default_branch(clone_dir, run_fn=ctx.run_fn)
    if branch is None:
        set_entry_error(ctx, "could not detect default branch")
        _cleanup_temp(ctx)
        return False
    ctx.entry_state.repos[0].default_branch = branch
    ctx.entry_state.tasks_completed["default_branch"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    return False
