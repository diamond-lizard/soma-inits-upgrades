"""Per-entry diff and cleanup tasks."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


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
