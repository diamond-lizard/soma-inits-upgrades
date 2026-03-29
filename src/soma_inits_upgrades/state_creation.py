"""Entry state creation and version compatibility check."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.validation_schema import FlatEntryDict


def _check_state_version(path: Path) -> None:
    """Exit with code 1 if state file is valid JSON with incompatible schema."""
    import json

    from pydantic import ValidationError

    try:
        raw = path.read_text(encoding="utf-8")
        json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return
    try:
        EntryState.model_validate_json(raw)
    except ValidationError:
        print(
            "State files appear to be from an incompatible version. "
            "Delete .state/ and .tmp/ directories and restart.",
            file=sys.stderr,
        )
        sys.exit(1)


def create_entry_state_if_missing(
    entry_dict: FlatEntryDict, state_dir: Path,
) -> bool:
    """Create a per-entry state file if missing or corrupt.

    Returns True if a state file was created/recreated, False if valid.
    Exits with code 1 if the existing state file is from an
    incompatible version (schema validation failure).
    """
    path = state_dir / f"{entry_dict['init_file']}.json"
    if path.exists():
        _check_state_version(path)
        existing = read_entry_state(path)
        if existing is not None:
            return False
        print(f"Warning: recreating corrupt state for {path}", file=sys.stderr)
    state = EntryState(
        init_file=entry_dict["init_file"],
        repos=[RepoState(
            repo_url=entry_dict["repo_url"],
            pinned_ref=entry_dict["pinned_ref"],
        )],
    )
    atomic_write_json(path, state)
    return True
