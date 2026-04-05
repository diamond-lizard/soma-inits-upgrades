"""Repo-level processing helpers: per-repo status and self-healing."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint_error, eprint_warn
from soma_inits_upgrades.processing_helpers import SELF_HEALING_LIMIT

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import RepoContext


def set_repo_done_early(
    repo_ctx: RepoContext, done_reason: str, notes: str,
) -> None:
    """Set per-repo early-completion fields and persist state."""
    from soma_inits_upgrades.state import atomic_write_json

    repo_ctx.repo_state.done_reason = done_reason
    repo_ctx.repo_state.notes = notes
    atomic_write_json(repo_ctx.entry_ctx.entry_state_path, repo_ctx.entry_ctx.entry_state)


def set_repo_error(
    repo_ctx: RepoContext, message: str,
    exc: BaseException | None = None,
) -> None:
    """Set per-repo error fields and persist state.

    When exc is provided, appends the exception origin (file, line,
    function) to the message as an [origin: ...] suffix.
    """
    from soma_inits_upgrades.state import atomic_write_json
    if exc is not None and exc.__traceback__ is not None:
        import traceback
        from pathlib import Path
        tb = traceback.extract_tb(exc.__traceback__)
        last = tb[-1]
        origin = Path(last.filename).name
        message = f"{message} [origin: {origin}:{last.lineno} in {last.name}]"
    repo_ctx.repo_state.done_reason = "error"
    repo_ctx.repo_state.notes = message
    atomic_write_json(repo_ctx.entry_ctx.entry_state_path, repo_ctx.entry_ctx.entry_state)


def self_heal_repo_resource(
    resource_path: Path, creating_task: str, repo_ctx: RepoContext,
) -> bool:
    """Check if a Tier 1 resource exists; reset its repo task if missing.

    Returns True if a reset was triggered (caller should return early).
    Returns False if the resource exists (proceed normally).
    """
    if resource_path.exists():
        return False
    if not repo_ctx.repo_state.tier1_tasks_completed.get(creating_task, False):
        return False
    repo_ctx.repo_state.tier1_tasks_completed[creating_task] = False
    count = repo_ctx.reset_counters.get(creating_task, 0) + 1
    repo_ctx.reset_counters[creating_task] = count
    if count >= SELF_HEALING_LIMIT:
        set_repo_error(
            repo_ctx, f"self-healing limit exceeded: {resource_path.name} missing "
            f"{count} times for {repo_ctx.entry_ctx.entry_state.init_file}",
        )
        name = repo_ctx.entry_ctx.entry_state.init_file
        eprint_error(
            f"FATAL: {resource_path.name} could not be regenerated "
            f"for {name} after "
            f"{count} attempts. Fix the underlying issue "
            f"(network, permissions, upstream repo) and re-run.",
        )
        sys.exit(1)
    name = repo_ctx.entry_ctx.entry_state.init_file
    eprint_warn(
        f"Warning: {resource_path.name} missing, re-executing {creating_task} "
        f"for {name} (attempt {count}/{SELF_HEALING_LIMIT})",
    )
    return True
