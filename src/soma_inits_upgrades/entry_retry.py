"""Entry retry and reset: phase resets for new entries, retry errored entries."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState, RepoState
    from soma_inits_upgrades.validation_schema import FlatEntryDict


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
    """Reset done_reason to None for repos with error status."""
    for repo in repos:
        if repo.done_reason == "error":
            repo.done_reason = None


def retry_errored_entries(results: list[FlatEntryDict], state_dir: Path) -> int:
    """Retry error-status entries with remaining retries.

    Resets status to in_progress, decrements retries_remaining.
    Returns count of retried entries.
    """
    from soma_inits_upgrades.state import atomic_write_json, read_entry_state
    retried = 0
    for entry in results:
        name = entry["init_file"]
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is None or state.status != "error":
            continue
        if state.retries_remaining <= 0:
            print(f"Skipping {name}: no retries remaining ({state.notes})", file=sys.stderr)
            continue
        state.retries_remaining -= 1
        state.status = "in_progress"
        state.notes = None
        state.done_reason = None
        _reset_errored_repo_reasons(state.repos)
        atomic_write_json(path, state)
        print(f"Retrying {name} ({state.retries_remaining} retries remaining)", file=sys.stderr)
        retried += 1
    return retried
