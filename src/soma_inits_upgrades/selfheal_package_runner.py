"""Orchestrator for package-name self-healing checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.selfheal_package_name import (
    check_multi_package_count,
    check_package_name_mismatch,
    reset_entry_for_reprocessing,
)
from soma_inits_upgrades.use_package_parser import extract_use_package_names

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def run_package_selfheal(ctx: EntryContext) -> None:
    """Run package-name and multi-package self-healing checks.

    Called by run_entry_task_loop after _reset_tier1_on_restart.
    Extracts use-package names from the init file, runs both
    detection checks, and resets the entry if a problem is found.
    """
    if ctx.inits_dir is None:
        return
    init_path = ctx.inits_dir / ctx.entry_state.init_file
    declared = extract_use_package_names(init_path)
    if not declared:
        return
    reason = check_package_name_mismatch(declared, ctx.entry_state)
    if reason is None:
        reason = check_multi_package_count(declared, ctx.entry_state)
    if reason is not None:
        reset_entry_for_reprocessing(ctx.entry_state, ctx.entry_state_path, reason)
