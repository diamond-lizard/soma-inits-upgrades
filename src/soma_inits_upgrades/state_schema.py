"""Pydantic state models and task-order constants."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Phases(BaseModel):
    """Runtime execution stage statuses."""

    setup: str = "pending"
    entry_processing: str = "pending"
    graph_finalization: str = "pending"
    summary: str = "pending"


class EntriesSummary(BaseModel):
    """Aggregate counts of per-entry statuses."""

    total: int = 0
    done: int = 0
    in_progress: int = 0
    pending: int = 0
    error: int = 0


class GraphFinalizationTasks(BaseModel):
    """Sub-task flags for graph finalization stage."""

    inversion: bool = False
    validation: bool = False
    completion: bool = False


class SummaryTasks(BaseModel):
    """Sub-task flags for summary stage."""

    security_summary: bool = False
    version_conflicts: bool = False
    completion: bool = False


class GlobalState(BaseModel):
    """Global state file structure."""

    emacs_version: str = ""
    stale_inits_file: str = ""
    phases: Phases = Field(default_factory=Phases)
    current_entry: str | None = None
    entries_summary: EntriesSummary = Field(default_factory=EntriesSummary)
    graph_finalization_tasks: GraphFinalizationTasks = Field(
        default_factory=GraphFinalizationTasks,
    )
    summary_tasks: SummaryTasks = Field(default_factory=SummaryTasks)
    entry_names: list[str] = Field(default_factory=list)
    completed: bool = False
    date_completed: str | None = None


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
