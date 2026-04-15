"""DI Protocol types and EntryContext model."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeAlias, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from soma_inits_upgrades.state_schema import EntryState, GlobalState
from soma_inits_upgrades.validation_schema import GroupedEntryDict

if TYPE_CHECKING:
    import subprocess

    from soma_inits_upgrades.state_schema import RepoState


@runtime_checkable
class SubprocessRunner(Protocol):
    """Protocol for subprocess.run-compatible callables."""

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]: ...


@runtime_checkable
class XclipChecker(Protocol):
    """Protocol for xclip availability checker."""

    def __call__(self) -> bool: ...


@runtime_checkable
class UserInputFn(Protocol):
    """Protocol for user input functions."""

    def __call__(self, prompt: str) -> str: ...


@runtime_checkable
class WhichFn(Protocol):
    """Protocol for shutil.which-compatible callables."""

    def __call__(self, name: str) -> str | None: ...


class EntryContext(BaseModel):
    """Bundles commonly-passed parameters for per-entry task processing."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    entry_state: EntryState
    entry_state_path: Path
    global_state: GlobalState
    global_state_path: Path
    entry_idx: int
    total: int
    output_dir: Path
    tmp_dir: Path
    state_dir: Path
    init_stem: str
    results: list[GroupedEntryDict]
    xclip_checker: XclipChecker
    run_fn: SubprocessRunner
    input_fn: UserInputFn | None = None
    reset_counters: dict[str, int] = Field(default_factory=dict)
    inits_dir: Path | None = None


@dataclass
class RepoContext:
    """Per-repo context for Tier 1 task handlers."""

    entry_ctx: EntryContext
    repo_state: RepoState
    temp_dir: Path
    clone_dir: Path
    reset_counters: dict[str, int] = field(default_factory=dict)


Tier1TaskHandler: TypeAlias = Callable[[RepoContext], bool]
"""Type alias for Tier 1 per-repo task handler functions."""

@runtime_checkable
class Tier2TaskHandler(Protocol):
    """Protocol for Tier 2 per-entry task handler functions."""

    def __call__(self, ctx: EntryContext) -> bool: ...
