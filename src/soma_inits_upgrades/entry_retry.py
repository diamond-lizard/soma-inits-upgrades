"""Entry retry and reset: phase resets for new entries, retry errored entries."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from soma_inits_upgrades.protocols import UserInputFn
    from soma_inits_upgrades.state_schema import GlobalState, RepoState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def _default_input(prompt: str) -> str:
    """Thin wrapper around input() for DI default."""
    return input(prompt)

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


def _prompt_exhausted_entry(
    name: str, notes: str | None, resolved_fn: UserInputFn,
) -> Literal["skip", "retry", "fresh"]:
    """Prompt user for action when entry retries are exhausted."""
    actions: dict[str, Literal["skip", "retry", "fresh"]] = {
        "1": "skip", "2": "retry", "3": "fresh",
    }
    print(f"\n{name}: retries exhausted.", file=sys.stderr)
    if notes:
        print(f"  Last error: {notes}", file=sys.stderr)
    print("  1) Skip this entry", file=sys.stderr)
    print("  2) Retry once more", file=sys.stderr)
    print("  3) Delete state and start fresh", file=sys.stderr)
    while True:
        try:
            choice = resolved_fn("Choose [1/2/3]: ").strip()
        except EOFError:
            return "skip"
        if choice in actions:
            return actions[choice]
        print(
            "Please enter a number (1, 2, or 3).",
            file=sys.stderr,
        )


def _handle_exhausted_entry(
    name: str, notes: str | None, path: Path,
    input_fn: UserInputFn | None,
) -> bool:
    """Handle entry with exhausted retries. Return True to retry."""
    resolved = input_fn if input_fn is not None else _default_input
    action = _prompt_exhausted_entry(name, notes, resolved)
    if action == "retry":
        return True
    if action == "fresh":
        path.unlink(missing_ok=True)
        print(
            f"Deleted state for {name}"
            " — will be recreated from scratch",
            file=sys.stderr,
        )
        return False
    print(f"Skipping {name} (user request)", file=sys.stderr)
    return False
def retry_errored_entries(
    results: list[GroupedEntryDict], state_dir: Path,
    input_fn: UserInputFn | None = None,
) -> int:
    """Retry error-status entries with remaining retries.

    Resets status to in_progress, decrements retries_remaining.
    Prompts interactively when retries are exhausted.
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
        exhausted = state.retries_remaining <= 0
        if exhausted and not _handle_exhausted_entry(name, state.notes, path, input_fn):
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
