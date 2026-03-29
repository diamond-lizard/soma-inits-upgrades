"""Global state Pydantic models: phases, summaries, and GlobalState."""

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
