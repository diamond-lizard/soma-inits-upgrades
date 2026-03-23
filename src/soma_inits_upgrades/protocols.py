"""DI Protocol types and EntryContext model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from soma_inits_upgrades.state_schema import EntryState, GlobalState  # noqa: TC001

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path


@runtime_checkable
class SubprocessRunner(Protocol):
    """Protocol for subprocess.run-compatible callables."""

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]: ...


@runtime_checkable
class TaskHandler(Protocol):
    """Protocol for per-entry task handler functions."""

    def __call__(self, ctx: EntryContext) -> bool: ...


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
    results: list[dict[str, str]]
    xclip_checker: XclipChecker
    run_fn: SubprocessRunner
    input_fn: UserInputFn | None = None
    reset_counters: dict[str, int] = Field(default_factory=dict)
