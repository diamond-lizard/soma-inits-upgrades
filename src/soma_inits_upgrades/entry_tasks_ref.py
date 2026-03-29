"""Per-entry git task: latest ref resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


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
        branch = ctx.entry_state.repos[0].default_branch
        set_entry_error(ctx, f"could not resolve latest ref on branch {branch}")
        _cleanup_temp(ctx)
        return False
    ctx.entry_state.repos[0].latest_ref = latest
    if is_pin_current(ctx.entry_state.repos[0].pinned_ref, latest):
        msg = "pinned ref is already at latest commit - no upgrade needed"
        set_entry_done_early(ctx, "already_latest", msg)
        _cleanup_temp(ctx)
        return False
    if not verify_pinned_ref(ctx):
        pin = ctx.entry_state.repos[0].pinned_ref
        set_entry_error(ctx, f"pinned ref {pin} does not exist in repository")
        _cleanup_temp(ctx)
        return False
    ctx.entry_state.tasks_completed["latest_ref"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    return False
