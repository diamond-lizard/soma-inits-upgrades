"""Setup stage: global state init, Emacs version prompt, directory creation."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import UserInputFn
    from soma_inits_upgrades.state_schema import GlobalState


def _default_prompt_fn(prompt: str) -> str:
    """Thin wrapper around click.prompt for dependency injection."""
    import click
    return str(click.prompt(prompt))


def initialize_global_state(
    global_state: GlobalState | None,
    global_state_path: Path,
    resolved_stale_path: Path,
) -> GlobalState:
    """Create or update the global state file for setup.

    If no global state exists, creates one with defaults.  Sets
    phases.setup to in_progress and records the stale inits path.
    Returns the (possibly new) global state.
    """
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_schema import GlobalState as GSModel

    if global_state is None:
        global_state = GSModel()
    global_state.phases.setup = "in_progress"
    global_state.stale_inits_file = str(resolved_stale_path)
    atomic_write_json(global_state_path, global_state)
    return global_state


def prompt_emacs_version(
    global_state: GlobalState,
    global_state_path: Path,
    prompt_fn: UserInputFn | None = None,
) -> None:
    """Prompt for Emacs version if not already recorded.

    Validates input via packaging.version.Version.  Re-prompts on
    invalid input.  Writes validated version to global state.
    """
    if global_state.emacs_version:
        return
    fn = prompt_fn or _default_prompt_fn
    from packaging.version import InvalidVersion, Version

    from soma_inits_upgrades.state import atomic_write_json

    while True:
        raw = fn("Enter your Emacs version (e.g. 29.1)")
        try:
            Version(raw)
        except InvalidVersion:
            print(f"Error: {raw!r} is not a valid version.", file=sys.stderr)
            continue
        global_state.emacs_version = raw
        atomic_write_json(global_state_path, global_state)
        return


def create_tmp_directory(output_dir: Path) -> None:
    """Create the .tmp/ directory under the output directory."""
    (output_dir / ".tmp").mkdir(parents=True, exist_ok=True)

