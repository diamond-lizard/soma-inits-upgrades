"""Entry retry and reset: phase resets for new entries, retry errored entries."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import UserInputFn
    from soma_inits_upgrades.state_schema import GlobalState, RepoState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def reset_phases_for_new_entries(
    global_state: GlobalState, new_names: list[str],
) -> None:
    """Reset downstream phases and add new entry names to global state.

    Sets entry_processing to in_progress and appends truly new names.
    """
    from soma_inits_upgrades.state_lifecycle import reset_downstream_phases
    reset_downstream_phases(global_state)
    global_state.phases.entry_processing = "in_progress"
    for name in new_names:
        if name not in global_state.entry_names:
            global_state.entry_names.append(name)
    count = len(new_names)
    print(f"Detected {count} new/modified entries, resuming processing", file=sys.stderr)


def _reset_errored_repo_reasons(repos: list[RepoState]) -> None:
    """Reset tier1_tasks_completed and done_reason for errored repos."""
    for repo in repos:
        if repo.done_reason == "error":
            for key in repo.tier1_tasks_completed:
                repo.tier1_tasks_completed[key] = False
            repo.done_reason = None


def retry_errored_entries(
    results: list[GroupedEntryDict], state_dir: Path,
    input_fn: UserInputFn | None = None,
) -> int:
    """Retry error-status entries with remaining retries.

    Resets status to in_progress, decrements retries_remaining.
    Prompts interactively when retries are exhausted.
    Returns count of retried entries.
    """
    from soma_inits_upgrades.entry_retry_prompt import handle_exhausted_entry
    from soma_inits_upgrades.state import atomic_write_json, read_entry_state
    retried = 0
    for entry in results:
        name = entry["init_file"]
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is None or state.status != "error":
            continue
        exhausted = state.retries_remaining <= 0
        if exhausted and not handle_exhausted_entry(name, state.notes, path, input_fn):
            continue
        if not exhausted:
            state.retries_remaining -= 1
        label = "user request" if exhausted else f"{state.retries_remaining} retries remaining"
        state.status = "in_progress"
        state.notes = None
        state.done_reason = None
        _reset_errored_repo_reasons(state.repos)
        atomic_write_json(path, state)
        print(f"Retrying {name} ({label})", file=sys.stderr)
        retried += 1
    return retried
