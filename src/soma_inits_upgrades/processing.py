"""Per-Entry Processing stage: entry loop, task dispatch, TASK_HANDLERS dict."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks import task_clone, task_default_branch
from soma_inits_upgrades.entry_tasks_analysis import task_deps, task_version_check
from soma_inits_upgrades.entry_tasks_diff import task_cleanup, task_diff
from soma_inits_upgrades.entry_tasks_graph import task_graph_update
from soma_inits_upgrades.entry_tasks_llm import (
    task_security_review,
    task_upgrade_analysis,
)
from soma_inits_upgrades.entry_tasks_ref import task_latest_ref
from soma_inits_upgrades.entry_tasks_report import task_upgrade_report
from soma_inits_upgrades.entry_tasks_symbols import task_symbols
from soma_inits_upgrades.output_validation_tasks import task_validate_outputs
from soma_inits_upgrades.state_schema import TASK_ORDER

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext, TaskHandler

TASK_HANDLERS: dict[str, TaskHandler] = {
    "clone": task_clone,
    "default_branch": task_default_branch,
    "latest_ref": task_latest_ref,
    "diff": task_diff,
    "deps": task_deps,
    "version_check": task_version_check,
    "security_review": task_security_review,
    "symbols": task_symbols,
    "upgrade_analysis": task_upgrade_analysis,
    "upgrade_report": task_upgrade_report,
    "graph_update": task_graph_update,
    "validate_outputs": task_validate_outputs,
    "cleanup": task_cleanup,
}


def find_next_task(tasks_completed: dict[str, bool]) -> str | None:
    """Return the first incomplete task name, or None if all done."""
    for task in TASK_ORDER:
        if not tasks_completed.get(task, False):
            return task
    return None


def run_entry_task_loop(ctx: EntryContext) -> bool:
    """Execute the per-entry task while-loop. Returns needs_rerun."""
    from soma_inits_upgrades.processing_helpers import check_progress, set_entry_error
    needs_rerun = False
    while True:
        status = ctx.entry_state.status
        if status in ("done", "error"):
            break
        task_name = find_next_task(ctx.entry_state.tasks_completed)
        if task_name is None:
            break
        completed_before = sum(ctx.entry_state.tasks_completed.values())
        try:
            result = TASK_HANDLERS[task_name](ctx)
            needs_rerun = needs_rerun or result
        except Exception as exc:
            set_entry_error(ctx, f"internal error in task {task_name}: {exc}")
            break
        if not check_progress(
            completed_before, ctx.entry_state.tasks_completed,
            ctx.entry_state.status,
        ):
            name = ctx.entry_state.init_file
            set_entry_error(ctx, f"internal error: no progress made processing {name}")
            break
    return needs_rerun


def _validate_handlers() -> None:
    """Validate TASK_HANDLERS keys match TASK_ORDER."""
    handler_keys = set(TASK_HANDLERS.keys())
    order_keys = set(TASK_ORDER)
    if handler_keys != order_keys:
        missing = order_keys - handler_keys
        extra = handler_keys - order_keys
        raise ValueError(f"Missing handlers: {missing}; Extra handlers: {extra}")
