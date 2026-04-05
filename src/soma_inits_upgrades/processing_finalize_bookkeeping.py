"""Entry completion bookkeeping: status updates and global state writes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def complete_entry_bookkeeping(ctx: EntryContext) -> None:
    """Update global state and write files for a done entry."""
    from soma_inits_upgrades.state import atomic_write_json
    ctx.entry_state.status = "done"
    ctx.global_state.entries_summary.in_progress -= 1
    ctx.global_state.entries_summary.done += 1
    ctx.global_state.current_entry = _next_pending_entry(ctx)
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    atomic_write_json(ctx.global_state_path, ctx.global_state)
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    eprint(f"{label} {ctx.entry_state.init_file}: done")


def _next_pending_entry(ctx: EntryContext) -> str | None:
    """Return the next pending entry name, or None."""
    from soma_inits_upgrades.state import read_entry_state
    for name in ctx.global_state.entry_names:
        path = ctx.state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is not None and state.status in ("pending", "in_progress"):
            return name
    return None
