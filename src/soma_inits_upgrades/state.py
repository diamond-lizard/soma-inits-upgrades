"""State file I/O: atomic writes, read-with-validation, task completion/reset."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from soma_inits_upgrades.state_schema import (
    EntriesSummary,
    EntryState,
    GlobalState,
)

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import RepoState


def read_global_state(path: Path) -> GlobalState | None:
    """Read and validate the global state file, or None if missing."""
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        return GlobalState.model_validate_json(raw)
    except (ValueError, OSError) as exc:
        print(f"Warning: invalid global state at {path}: {exc}", file=sys.stderr)
        return None


def atomic_write_json(path: Path, data: BaseModel | dict[str, Any]) -> None:
    """Write data to a JSON file atomically via tmp+rename.

    Accepts a Pydantic BaseModel or a plain dict.
    """
    if isinstance(data, BaseModel):
        content = data.model_dump_json(indent=2)
    else:
        import json
        content = json.dumps(data, indent=2)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.rename(path)


def read_entry_state(path: Path) -> EntryState | None:
    """Read and validate a per-entry state file, or None if missing."""
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        return EntryState.model_validate_json(raw)
    except (ValueError, OSError) as exc:
        print(f"Warning: invalid entry state at {path}: {exc}", file=sys.stderr)
        return None


def mark_task_complete(state: EntryState, task_id: str, path: Path) -> None:
    """Mark a per-entry task as completed and write state atomically."""
    state.tasks_completed[task_id] = True
    atomic_write_json(path, state)


def mark_repo_task_complete(
    state: EntryState, repo_state: RepoState, task_id: str, path: Path,
) -> None:
    """Mark a per-repo Tier 1 task as completed and write state atomically."""
    repo_state.tier1_tasks_completed[task_id] = True
    atomic_write_json(path, state)


def reset_task(state: EntryState, task_id: str, path: Path) -> None:
    """Reset a per-entry task to incomplete and write state atomically."""
    state.tasks_completed[task_id] = False
    atomic_write_json(path, state)


def reconcile_entries_summary(entry_names: list[str], state_dir: Path) -> EntriesSummary:
    """Count entry statuses by reading per-entry state files."""
    keys = ("total", "done", "in_progress", "pending", "error")
    counts: dict[str, int] = dict.fromkeys(keys, 0)
    for name in entry_names:
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is None:
            counts["pending"] += 1
        elif state.status in counts:
            counts[state.status] += 1
        else:
            counts["pending"] += 1
        counts["total"] += 1
    return EntriesSummary(**counts)
