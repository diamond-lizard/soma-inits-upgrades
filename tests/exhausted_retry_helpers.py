"""Shared helpers for exhausted-retry tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

_URL = "https://forge.test/r"


def errored_state(name: str = "x.el") -> EntryState:
    """Build an errored EntryState with exhausted retries."""
    rs = RepoState(
        repo_url=_URL, pinned_ref="a",
        done_reason="error", package_name="some-pkg",
    )
    for k in rs.tier1_tasks_completed:
        rs.tier1_tasks_completed[k] = True
    return EntryState(
        init_file=name, repos=[rs],
        status="error", retries_remaining=0,
        notes="some failure",
    )


def entry_dict(name: str = "x.el") -> dict[str, object]:
    """Build a GroupedEntryDict for testing."""
    return {
        "init_file": name,
        "repos": [{"repo_url": _URL, "pinned_ref": "a"}],
    }


def write_states(tmp_path: Path, *states: EntryState) -> Path:
    """Write entry states to a temp state dir, return the dir."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True, exist_ok=True)
    for es in states:
        atomic_write_json(sd / f"{es.init_file}.json", es)
    return sd
