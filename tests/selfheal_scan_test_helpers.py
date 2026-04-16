"""Shared helpers for self-healing scan tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def make_done_entry(
    state_dir: Path, init_file: str, pkg_name: str,
) -> None:
    """Write a 'done' entry state with one repo to state_dir."""
    es = EntryState(
        init_file=init_file,
        repos=[RepoState(
            repo_url="https://forge.test/r",
            pinned_ref="a",
            package_name=pkg_name,
        )],
    )
    es.status = "done"
    es.done_reason = "completed_normally"
    es.notes = "all tasks finished"
    atomic_write_json(state_dir / f"{init_file}.json", es)
