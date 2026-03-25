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
    print(f"[{idx}/{total}] {name}: cloning {ctx.entry_state.repo_url}...", file=sys.stderr)
    clone_dir = ctx.tmp_dir / ctx.init_stem
    success, error_msg = clone_repo(
        ctx.entry_state.repo_url, clone_dir, ctx.output_dir, run_fn=ctx.run_fn,
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
    ctx.entry_state.default_branch = branch
    ctx.entry_state.tasks_completed["default_branch"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    return False


def task_latest_ref(ctx: EntryContext) -> bool:
    """Resolve latest ref and check if pin is current."""
    if ctx.entry_state.tasks_completed.get("latest_ref", False):
        return False
    from soma_inits_upgrades.entry_tasks_diff import (
        _cleanup_temp,
        is_pin_current,
        resolve_latest_ref,
        verify_pinned_ref,
    )
    from soma_inits_upgrades.processing_helpers import (
        self_heal_resource,
        set_entry_done_early,
        set_entry_error,
    )
    from soma_inits_upgrades.state import atomic_write_json
    clone_dir = ctx.tmp_dir / ctx.init_stem
    if self_heal_resource(clone_dir, "clone", ctx):
        return False
    latest = resolve_latest_ref(ctx)
    if latest is None:
        branch = ctx.entry_state.default_branch
        set_entry_error(ctx, f"could not resolve latest ref on branch {branch}")
        _cleanup_temp(ctx)
        return False
    ctx.entry_state.latest_ref = latest
    if is_pin_current(ctx.entry_state.pinned_ref, latest):
        msg = "pinned ref is already at latest commit - no upgrade needed"
        set_entry_done_early(ctx, "already_latest", msg)
        _cleanup_temp(ctx)
        return False
    if not verify_pinned_ref(ctx):
        pin = ctx.entry_state.pinned_ref
        set_entry_error(ctx, f"pinned ref {pin} does not exist in repository")
        _cleanup_temp(ctx)
        return False
    ctx.entry_state.tasks_completed["latest_ref"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    return False
