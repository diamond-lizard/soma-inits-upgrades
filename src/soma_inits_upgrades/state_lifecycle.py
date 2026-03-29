"""Entry state lifecycle: creation, field change detection, reset."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_artifacts import delete_entry_artifacts
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.validation_schema import FlatEntryDict




def detect_entry_field_changes(
    state: EntryState, entry_dict: FlatEntryDict,
) -> list[str]:
    """Compare repo_url and pinned_ref between state and entry dict.

    Returns a list of field names that differ.
    """
    changed: list[str] = []
    if state.repos[0].repo_url != entry_dict["repo_url"]:
        changed.append("repo_url")
    if state.repos[0].pinned_ref != entry_dict["pinned_ref"]:
        changed.append("pinned_ref")
    return changed


def reset_entry_state_if_modified(
    entry_dict: FlatEntryDict, state_dir: Path, output_dir: Path,
) -> bool:
    """Reset entry state if repo_url or pinned_ref changed.

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
        f"Warning: {entry_dict['init_file']} changed ({fields}), resetting",
        file=sys.stderr,
    )
    delete_entry_artifacts(entry_dict["init_file"], output_dir)
    new_state = EntryState(
        init_file=entry_dict["init_file"],
        repos=[RepoState(
            repo_url=entry_dict["repo_url"],
            pinned_ref=entry_dict["pinned_ref"],
        )],
    )
    atomic_write_json(path, new_state)
    return True
