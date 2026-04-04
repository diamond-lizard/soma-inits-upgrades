"""Interactive prompt for entries with exhausted retries."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from soma_inits_upgrades.protocols import UserInputFn


def _default_input(prompt: str) -> str:
    """Thin wrapper around input() for DI default."""
    return input(prompt)


def _prompt_exhausted_entry(
    name: str, notes: str | None, resolved_fn: UserInputFn,
) -> Literal["skip", "retry", "fresh"]:
    """Prompt user for action when entry retries are exhausted."""
    actions: dict[str, Literal["skip", "retry", "fresh"]] = {
        "1": "skip", "2": "retry", "3": "fresh",
    }
    print(f"\n{name}: retries exhausted.", file=sys.stderr)
    if notes:
        print(f"  Last error: {notes}", file=sys.stderr)
    print("  1) Skip this entry", file=sys.stderr)
    print("  2) Retry once more", file=sys.stderr)
    print("  3) Delete state and start fresh", file=sys.stderr)
    while True:
        try:
            choice = resolved_fn("Choose [1/2/3]: ").strip()
        except EOFError:
            return "skip"
        if choice in actions:
            return actions[choice]
        print(
            "Please enter a number (1, 2, or 3).",
            file=sys.stderr,
        )


def handle_exhausted_entry(
    name: str, notes: str | None, path: Path,
    input_fn: UserInputFn | None,
) -> bool:
    """Handle entry with exhausted retries. Return True to retry."""
    resolved = input_fn if input_fn is not None else _default_input
    action = _prompt_exhausted_entry(name, notes, resolved)
    if action == "retry":
        return True
    if action == "fresh":
        path.unlink(missing_ok=True)
        print(
            f"Deleted state for {name}"
            " — will be recreated from scratch",
            file=sys.stderr,
        )
        return False
    print(f"Skipping {name} (user request)", file=sys.stderr)
    return False
