"""Per-entry git tasks: clone, default branch, latest ref, diff, cleanup."""

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
    return False


def task_default_branch(ctx: EntryContext) -> bool:
    """Detect the default branch of the cloned repository."""
    if ctx.entry_state.tasks_completed.get("default_branch", False):
        return False
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


def resolve_latest_ref(ctx: EntryContext) -> str | None:
    """Resolve the latest commit SHA on the default branch."""
    from soma_inits_upgrades.git_ref_ops import rev_parse

    clone_dir = ctx.tmp_dir / ctx.init_stem
    return rev_parse(clone_dir, f"origin/{ctx.entry_state.default_branch}", run_fn=ctx.run_fn)


def is_pin_current(pinned_ref: str, latest_ref: str) -> bool:
    """Return True if pinned ref equals latest ref."""
    return pinned_ref == latest_ref


def verify_pinned_ref(ctx: EntryContext) -> bool:
    """Verify the pinned ref exists in the repository."""
    from soma_inits_upgrades.git_ref_ops import verify_ref

    clone_dir = ctx.tmp_dir / ctx.init_stem
    return verify_ref(clone_dir, ctx.entry_state.pinned_ref, run_fn=ctx.run_fn)


def task_latest_ref(ctx: EntryContext) -> bool:
    """Resolve latest ref and check if pin is current."""
    if ctx.entry_state.tasks_completed.get("latest_ref", False):
        return False
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


def task_diff(ctx: EntryContext) -> bool:
    """Generate the diff between pinned and latest refs."""
    if ctx.entry_state.tasks_completed.get("diff", False):
        return False
    from soma_inits_upgrades.git_cleanup import generate_diff
    from soma_inits_upgrades.processing_helpers import (
        self_heal_resource,
        set_entry_done_early,
        set_entry_error,
    )
    from soma_inits_upgrades.state import mark_task_complete

    clone_dir = ctx.tmp_dir / ctx.init_stem
    if self_heal_resource(clone_dir, "clone", ctx):
        return False
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    print(f"{label} {ctx.entry_state.init_file}: generating diff...", file=sys.stderr)
    diff_path = ctx.tmp_dir / f"{ctx.init_stem}.diff"
    try:
        has_diff = generate_diff(
            clone_dir, ctx.entry_state.pinned_ref, ctx.entry_state.latest_ref or "",
            diff_path, run_fn=ctx.run_fn,
        )
    except Exception as exc:
        set_entry_error(ctx, f"diff generation failed: {exc}")
        _cleanup_temp(ctx)
        return False
    if not has_diff:
        msg = "empty diff - no changes between pinned and latest ref"
        set_entry_done_early(ctx, "empty_diff", msg)
        _cleanup_temp(ctx)
        return False
    mark_task_complete(ctx.entry_state, "diff", ctx.entry_state_path)
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


def _cleanup_temp(ctx: EntryContext) -> None:
    """Delete temp artifacts on error or early exit."""
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts

    delete_entry_artifacts(
        ctx.entry_state.init_file, ctx.output_dir,
        include_permanent=False, include_temp=True,
    )
