"""Pydantic state models and task-order constants."""

from __future__ import annotations

from pydantic import BaseModel, Field

from soma_inits_upgrades.state_schema_global import (
    EntriesSummary as EntriesSummary,
)
from soma_inits_upgrades.state_schema_global import (
    GlobalState as GlobalState,
)
from soma_inits_upgrades.state_schema_global import (
    GraphFinalizationTasks as GraphFinalizationTasks,
)
from soma_inits_upgrades.state_schema_global import (
    Phases as Phases,
)
from soma_inits_upgrades.state_schema_global import (
    SummaryTasks as SummaryTasks,
)

TASK_ORDER: list[str] = [
    "clone", "default_branch", "latest_ref", "diff", "deps",
    "version_check", "security_review", "symbols", "upgrade_analysis",
    "upgrade_report", "graph_update", "validate_outputs", "cleanup",
]


def _default_tasks_completed() -> dict[str, bool]:
    """Build default tasks_completed dict from TASK_ORDER."""
    return dict.fromkeys(TASK_ORDER, False)



def _default_tier1_tasks_completed() -> dict[str, bool]:
    """Build default tier1_tasks_completed dict."""
    keys = [
        "clone", "default_branch", "latest_ref", "diff",
        "deps", "version_check", "symbols",
    ]
    return dict.fromkeys(keys, False)


class RepoState(BaseModel):
    """Per-repository state within an entry."""

    repo_url: str
    pinned_ref: str
    latest_ref: str | None = None
    default_branch: str | None = None
    package_name: str | None = None
    min_emacs_version: str | None = None
    emacs_upgrade_required: bool = False
    depends_on: list[str] | None = None
    done_reason: str | None = None
    notes: str | None = None
    tier1_tasks_completed: dict[str, bool] = Field(
        default_factory=_default_tier1_tasks_completed,
    )

class EntryState(BaseModel):
    """Per-entry state file structure."""

    init_file: str
    repos: list[RepoState] = Field(default_factory=list)
    status: str = "pending"
    notes: str | None = None
    done_reason: str | None = None
    retries_remaining: int = 5
    tasks_completed: dict[str, bool] = Field(default_factory=_default_tasks_completed)
