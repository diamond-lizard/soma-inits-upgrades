"""Batch scan of completed entries for self-healing opportunities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.selfheal_package_name import (
    check_multi_package_count,
    check_package_name_mismatch,
    reset_entry_for_reprocessing,
)
from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.use_package_parser import extract_use_package_names

if TYPE_CHECKING:
    from pathlib import Path


def scan_completed_entries_for_selfheal(
    entry_names: list[str],
    state_dir: Path,
    inits_dir: Path | None,
) -> list[str]:
    """Scan done entries for package-name or monorepo mismatches.

    Returns names of entries that were reset to 'pending'.
    Skips entries that are not 'done', have no init file on disk,
    or have no state file.
    """
    if inits_dir is None:
        return []
    reset_names: list[str] = []
    for name in entry_names:
        reason = _check_single_entry(name, state_dir, inits_dir)
        if reason is not None:
            reset_names.append(name)
    return reset_names


def _check_single_entry(
    name: str, state_dir: Path, inits_dir: Path,
) -> str | None:
    """Check one entry and reset it if a mismatch is found.

    Returns the reason string if reset, None otherwise.
    """
    esp = state_dir / f"{name}.json"
    es = read_entry_state(esp)
    if es is None or es.status != "done":
        return None
    init_path = inits_dir / es.init_file
    if not init_path.exists():
        return None
    declared = extract_use_package_names(init_path)
    if not declared:
        return None
    reason = check_package_name_mismatch(declared, es)
    if reason is None:
        reason = check_multi_package_count(declared, es)
    if reason is None:
        return None
    reset_entry_for_reprocessing(es, esp, reason)
    es.status = "pending"
    es.done_reason = None
    es.notes = None
    atomic_write_json(esp, es)
    return reason
