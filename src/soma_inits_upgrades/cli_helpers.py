#!/usr/bin/env python3
"""CLI helpers: path resolution, input validation, process locking."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint, eprint_error

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState
    from soma_inits_upgrades.validation_schema import GroupedEntryDict, RepoEntryDict


def resolve_and_validate_paths(
    stale_inits_path: str, output_dir: str,
) -> tuple[Path, Path]:
    """Resolve both paths to canonical absolute paths.

    Expands ~ via expanduser() before resolve() since resolve() treats
    ~ as a literal directory name.  Creates the .state/ subdirectory
    under the output directory.  Returns (resolved_stale_path, resolved_output_dir).
    """
    from pathlib import Path as _Path

    resolved_stale = _Path(stale_inits_path).expanduser().resolve()
    resolved_output = _Path(output_dir).expanduser().resolve()
    state_dir = resolved_output / ".state"
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        eprint_error(f"Error: cannot create output directory: {exc}")
        sys.exit(1)
    return resolved_stale, resolved_output


def check_stale_inits_mismatch(
    global_state: GlobalState | None, resolved_stale_path: Path,
) -> None:
    """Verify stale inits path matches previous run if setup is done.

    If the global state exists and phases.setup is done, checks that
    the resolved stale inits path matches the recorded path.  On
    mismatch, prints an error to stderr and exits with code 1.
    """
    if global_state is None or global_state.phases.setup != "done":
        return
    recorded = global_state.stale_inits_file
    if recorded and str(resolved_stale_path) != recorded:
        eprint_error(
            f"Error: stale inits file mismatch.\n"
            f"  Previous run used: {recorded}\n"
            f"  Current argument:  {resolved_stale_path}\n"
            f"Use the original file, or delete the .state/ directory "
            f"to start fresh.",
        )
        sys.exit(1)


def load_stale_inits(path: Path) -> list[GroupedEntryDict]:
    """Read, validate, and group the stale inits JSON file.

    Groups entries by init_file, returning one dict per unique
    init_file with a repos list.  Exits with code 1 on validation
    or JSON errors.  Exits with code 0 if results is empty.
    """
    from pydantic import ValidationError

    from soma_inits_upgrades.validation_schema import StaleInitsFile

    try:
        raw = path.read_text(encoding="utf-8")
        validated = StaleInitsFile.model_validate_json(raw)
    except FileNotFoundError:
        eprint_error(f"Error: stale inits file not found: {path}")
        sys.exit(1)
    except (ValidationError, ValueError) as exc:
        eprint_error(f"Error: invalid stale inits file: {exc}")
        sys.exit(1)
    if not validated.results:
        eprint("No stale entries found in input file.")
        sys.exit(0)
    grouped: dict[str, list[RepoEntryDict]] = {}
    for e in validated.results:
        repo: RepoEntryDict = {
            "repo_url": e.repo_url, "pinned_ref": e.pinned_ref,
        }
        grouped.setdefault(e.init_file, []).append(repo)
    return [
        {"init_file": name, "repos": repos}
        for name, repos in grouped.items()
    ]
