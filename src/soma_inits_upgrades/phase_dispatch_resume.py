"""Phase dispatch: resume completed entry processing."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import UserInputFn
    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict


def resume_completed_entry_processing(
    results: list[GroupedEntryDict], state_dir: Path,
    output_dir: Path, global_state: GlobalState,
    input_fn: UserInputFn | None = None,
) -> bool:
    """Handle entry_processing already done. Returns True to reprocess."""
    from soma_inits_upgrades.entry_changes import detect_new_or_modified_entries
    from soma_inits_upgrades.phase_dispatch import handle_detected_changes
    from soma_inits_upgrades.state import atomic_write_json

    new, modified, orphan_count = detect_new_or_modified_entries(
        results, state_dir, output_dir, global_state,
    )
    atomic_write_json(state_dir / "global.json", global_state)
    if handle_detected_changes(
        results, state_dir, output_dir, global_state,
        new, modified, orphan_count,
        input_fn=input_fn,
    ):
        return True
    from soma_inits_upgrades.phase_dispatch import handle_retryable_errors

    return handle_retryable_errors(results, state_dir, global_state, input_fn=input_fn)
