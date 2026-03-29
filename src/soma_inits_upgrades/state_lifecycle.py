"""Entry state lifecycle: creation, field change detection, reset."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_artifacts import delete_entry_artifacts
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def detect_entry_field_changes(
    state: EntryState, entry_dict: GroupedEntryDict,
) -> list[str]:
    """Compare repos between state and entry dict.

    Uses set-based comparison of (repo_url, pinned_ref) pairs.
    Returns ["repos"] if the sets differ, else [].
    """
    state_pairs = {
        (r.repo_url, r.pinned_ref) for r in state.repos
    }
    entry_pairs = {
        (r["repo_url"], r["pinned_ref"]) for r in entry_dict["repos"]
    }
    if state_pairs != entry_pairs:
        return ["repos"]
    return []


def reset_entry_state_if_modified(
    entry_dict: GroupedEntryDict, state_dir: Path, output_dir: Path,
) -> bool:
    """Reset entry state if repos changed.

    Returns True if the entry was modified and reset, False otherwise.
    """
    path = state_dir / f"{entry_dict['init_file']}.json"
    existing = read_entry_state(path)
    if existing is None:
        return False
    changed = detect_entry_field_changes(existing, entry_dict)
    if not changed:
        return False
    fields = ", ".join(changed)
    print(
        f"Warning: {entry_dict['init_file']} changed ({fields}),"
        f" resetting",
        file=sys.stderr,
    )
    delete_entry_artifacts(entry_dict["init_file"], output_dir)
    repos = [
        RepoState(repo_url=r["repo_url"], pinned_ref=r["pinned_ref"])
        for r in entry_dict["repos"]
    ]
    new_state = EntryState(
        init_file=entry_dict["init_file"], repos=repos,
    )
    atomic_write_json(path, new_state)
    return True


def reset_downstream_phases(global_state: GlobalState) -> None:
    """Reset entry_processing through summary, graph and completion flags."""
    from soma_inits_upgrades.state_schema import GraphFinalizationTasks, SummaryTasks

    global_state.phases.entry_processing = "pending"
    global_state.phases.graph_finalization = "pending"
    global_state.phases.summary = "pending"
    global_state.graph_finalization_tasks = GraphFinalizationTasks()
    global_state.summary_tasks = SummaryTasks()
    global_state.completed = False
    global_state.date_completed = None
