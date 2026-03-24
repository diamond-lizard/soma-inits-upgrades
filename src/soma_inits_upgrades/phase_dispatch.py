"""Phase dispatch lifecycle: viability checks and stage management."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import EntriesSummary


def check_processing_viability(
    entries_summary: EntriesSummary,
    entry_names: list[str],
    state_dir: Path,
) -> None:
    """Verify at least one entry succeeded before finalization.

    If zero entries completed (all errored or skipped), scans per-entry
    state files for error entries, prints a summary to stderr (one line
    per errored entry as '<init_file>: <notes>'), and exits with code 1.
    Returns normally if at least one entry succeeded.
    """
    if entries_summary.done >= 1:
        return
    from soma_inits_upgrades.state import read_entry_state

    print("Error: no entries were successfully processed.", file=sys.stderr)
    for name in entry_names:
        path = state_dir / f"{name}.json"
        state = read_entry_state(path)
        if state is not None and state.status == "error":
            notes = state.notes or "unknown error"
            print(f"  {state.init_file}: {notes}", file=sys.stderr)
    sys.exit(1)
