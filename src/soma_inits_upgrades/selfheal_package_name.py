"""Self-healing detection and reset for package name mismatches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint_warn
from soma_inits_upgrades.state import atomic_write_json

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import EntryState


def _collect_active_package_names(entry_state: EntryState) -> list[str]:
    """Return package_name values from non-done repos where set."""
    return [
        r.package_name
        for r in entry_state.repos
        if r.done_reason is None and r.package_name is not None
    ]


def check_package_name_mismatch(
    declared_names: list[str], entry_state: EntryState,
) -> str | None:
    """Detect stored package names absent from declared names.

    Returns a reason string if a mismatch is found, None otherwise.
    Pure detection: reads state but does not mutate it.
    """
    if not declared_names:
        return None
    stored = _collect_active_package_names(entry_state)
    if not stored:
        return None
    wrong = [n for n in stored if n not in declared_names]
    if not wrong:
        return None
    return (
        f"package name mismatch for {entry_state.init_file}:"
        f" stored {wrong} but init file declares {declared_names}"
    )


def check_multi_package_count(
    declared_names: list[str], entry_state: EntryState,
) -> str | None:
    """Detect missing monorepo entries by comparing declaration count.

    Returns a reason string if the count mismatch is found,
    None otherwise.  Pure detection: does not mutate state.
    """
    if not declared_names:
        return None
    if not _collect_active_package_names(entry_state):
        return None
    if entry_state.multi_package_verified:
        return None
    non_done = sum(1 for r in entry_state.repos if r.done_reason is None)
    if len(declared_names) <= non_done:
        return None
    return (
        f"missing multi-package entries for {entry_state.init_file}:"
        f" {len(declared_names)} declared but only {non_done} repos"
    )


def reset_entry_for_reprocessing(
    entry_state: EntryState, entry_state_path: Path, reason: str,
) -> None:
    """Perform full structural reset for package name re-processing.

    Removes monorepo-derived entries, resets all Tier 1/2/cleanup tasks
    on active repos, clears package fields, and persists state.
    """
    eprint_warn(reason)
    entry_state.repos = [
        r for r in entry_state.repos if not r.is_monorepo_derived
    ]
    for repo in entry_state.repos:
        if repo.done_reason is not None:
            continue
        for key in repo.tier1_tasks_completed:
            repo.tier1_tasks_completed[key] = False
        repo.package_name = None
        repo.depends_on = None
        repo.min_emacs_version = None
    for key in entry_state.tasks_completed:
        entry_state.tasks_completed[key] = False
    entry_state.multi_package_verified = False
    atomic_write_json(entry_state_path, entry_state)
