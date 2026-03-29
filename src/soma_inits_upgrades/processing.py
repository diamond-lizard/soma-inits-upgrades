"""Per-Entry Processing stage: entry loop, task dispatch, tier handler dicts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks import task_clone, task_default_branch
from soma_inits_upgrades.entry_tasks_analysis import task_deps, task_version_check
from soma_inits_upgrades.entry_tasks_diff import task_diff
from soma_inits_upgrades.entry_tasks_graph import task_graph_update
from soma_inits_upgrades.entry_tasks_llm import (
    task_security_review,
    task_upgrade_analysis,
)
from soma_inits_upgrades.entry_tasks_ref import task_latest_ref
from soma_inits_upgrades.entry_tasks_report import task_upgrade_report
from soma_inits_upgrades.entry_tasks_symbols import task_symbols
from soma_inits_upgrades.output_validation_tasks import task_validate_outputs
from soma_inits_upgrades.processing_runner import (
    run_entry_task_loop as run_entry_task_loop,
)
from soma_inits_upgrades.state_schema import TIER_1_TASKS, TIER_2_TASKS

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import (
        Tier1TaskHandler,
        Tier2TaskHandler,
    )

TIER_1_HANDLERS: dict[str, Tier1TaskHandler] = {
    "clone": task_clone,
    "default_branch": task_default_branch,
    "latest_ref": task_latest_ref,
    "diff": task_diff,
    "deps": task_deps,
    "version_check": task_version_check,
    "symbols": task_symbols,
}

TIER_2_HANDLERS: dict[str, Tier2TaskHandler] = {
    "security_review": task_security_review,
    "upgrade_analysis": task_upgrade_analysis,
    "upgrade_report": task_upgrade_report,
    "graph_update": task_graph_update,
    "validate_outputs": task_validate_outputs,
}


def find_next_tier1_task(tier1_tasks_completed: dict[str, bool]) -> str | None:
    """Return the first incomplete Tier 1 task name, or None if all done."""
    for task in TIER_1_TASKS:
        if not tier1_tasks_completed.get(task, False):
            return task
    return None


def find_next_tier2_task(tasks_completed: dict[str, bool]) -> str | None:
    """Return the first incomplete Tier 2 task name, or None if all done."""
    for task in TIER_2_TASKS:
        if not tasks_completed.get(task, False):
            return task
    return None




def _validate_handlers() -> None:
    """Validate handler dicts match their task constants."""
    for name, handlers, tasks in (
        ("TIER_1", TIER_1_HANDLERS, TIER_1_TASKS),
        ("TIER_2", TIER_2_HANDLERS, TIER_2_TASKS),
    ):
        keys = set(handlers.keys())
        expected = set(tasks)
        if keys != expected:
            missing = expected - keys
            extra = keys - expected
            raise ValueError(f"{name}: Missing: {missing}; Extra: {extra}")
