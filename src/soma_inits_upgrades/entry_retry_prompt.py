"""Interactive prompt for entries with exhausted retries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import (
    eprint,
    eprint_error,
    eprint_plain,
    eprint_prompt,
    eprint_warn,
)
from soma_inits_upgrades.protocols import default_input

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from soma_inits_upgrades.protocols import UserInputFn


def _prompt_exhausted_entry(
    name: str, notes: str | None, resolved_fn: UserInputFn,
) -> Literal["skip", "retry", "fresh"]:
    """Prompt user for action when entry retries are exhausted."""
    actions: dict[str, Literal["skip", "retry", "fresh"]] = {
        "1": "skip", "2": "retry", "3": "fresh",
    }
    eprint_warn(f"\n{name}: retries exhausted.")
    if notes:
        eprint_plain("  Last error: ", end="")
        eprint_error(notes)
    eprint_prompt("  1) Skip this entry")
    eprint_prompt("  2) Retry once more")
    eprint_prompt("  3) Delete state and start fresh")
    while True:
        try:
            choice = resolved_fn("Choose [1/2/3]: ").strip()
        except EOFError:
            return "skip"
        if choice in actions:
            return actions[choice]
        eprint_prompt("Please enter a number (1, 2, or 3).")


def handle_exhausted_entry(
    name: str, notes: str | None, path: Path,
    input_fn: UserInputFn | None,
) -> bool:
    """Handle entry with exhausted retries. Return True to retry."""
    resolved = input_fn if input_fn is not None else default_input
    action = _prompt_exhausted_entry(name, notes, resolved)
    if action == "retry":
        return True
    if action == "fresh":
        path.unlink(missing_ok=True)
        eprint(
            f"Deleted state for {name}"
            " — will be recreated from scratch",
        )
        return False
    eprint(f"Skipping {name} (user request)")
    return False
