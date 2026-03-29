"""Summary stage: entry categorization by final outcome."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def categorize_entries(
    entry_names: list[str], state_dir: Path,
) -> dict[str, list[str]]:
    """Categorize entries by their final outcome.

    Reads per-entry state files and groups entries into:
    'errored', 'empty_diff', 'skipped', 'already_latest', 'done'.
    """
    from soma_inits_upgrades.state import read_entry_state

    categories: dict[str, list[str]] = {
        "errored": [],
        "empty_diff": [],
        "skipped": [],
        "already_latest": [],
        "partial": [],
        "no_changes_needed": [],
        "done": [],
    }
    for name in entry_names:
        state = read_entry_state(state_dir / f"{name}.json")
        if state is None:
            continue
        if state.status == "error":
            note = f"{name}: {state.notes or 'unknown error'}"
            categories["errored"].append(note)
        elif state.done_reason == "empty_diff":
            categories["empty_diff"].append(name)
        elif state.done_reason == "skipped":
            categories["skipped"].append(name)
        elif state.done_reason == "already_latest":
            categories["already_latest"].append(name)
        elif state.done_reason == "partial":
            note = f"{name}: {state.notes or 'partial completion'}"
            categories["partial"].append(note)
        elif state.done_reason == "no_changes_needed":
            categories["no_changes_needed"].append(name)
        elif state.status == "done" and state.done_reason is None:
            categories["done"].append(name)
    return categories
