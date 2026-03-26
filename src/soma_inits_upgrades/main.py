"""Click CLI definition for soma-inits-upgrades."""

from __future__ import annotations

import signal
from functools import partial

import click


@click.command()
@click.argument("stale_inits_file", type=click.Path(exists=False))
@click.option(
    "--output-dir",
    default="~/.emacs.d/soma/inits-upgrades/",
    help="Output directory for reports and state.",
)
def cli(stale_inits_file: str, output_dir: str) -> None:
    """Automate security review and upgrade planning for stale elpaca pins.

    Reads STALE_INITS_FILE (a JSON file listing packages with outdated
    pinned refs), clones each repository, generates diffs, extracts
    symbols, and pauses at three LLM-assisted steps per entry:

    \b
    1. Security review -- paste the prompt into an LLM for analysis
    2. Upgrade analysis -- LLM identifies breaking changes
    3. Upgrade report -- LLM produces a human-readable summary

    Results are written to OUTPUT_DIR (default: ~/.emacs.d/soma/inits-upgrades/).
    Processing is fully resumable; re-run to continue from where you left off.
    """
    from pathlib import Path as _Path
    if _Path(stale_inits_file).expanduser().is_dir():
        raise click.UsageError(
            f"STALE_INITS_FILE '{stale_inits_file}' is a directory, not a file",
        )
    if not _Path(stale_inits_file).expanduser().exists():
        raise click.UsageError(
            f"STALE_INITS_FILE '{stale_inits_file}' does not exist",
        )

    from soma_inits_upgrades.cli_helpers import (
        check_stale_inits_mismatch,
        load_stale_inits,
        resolve_and_validate_paths,
    )
    from soma_inits_upgrades.process_lock import acquire_process_lock
    from soma_inits_upgrades.state import read_global_state
    from soma_inits_upgrades.subprocess_tracking import tracked_run
    from soma_inits_upgrades.subprocess_utils import ProcessTracker, make_sigterm_handler
    from soma_inits_upgrades.tool_checks import validate_tools

    tracker = ProcessTracker()
    signal.signal(signal.SIGTERM, make_sigterm_handler(tracker))
    run_fn = partial(tracked_run, tracker=tracker)
    validate_tools(run_fn)

    resolved_stale, resolved_output = resolve_and_validate_paths(
        stale_inits_file, output_dir,
    )
    state_dir = resolved_output / ".state"
    global_state_path = state_dir / "global.json"

    _lock_fd = acquire_process_lock(state_dir)
    global_state = read_global_state(global_state_path)
    check_stale_inits_mismatch(global_state, resolved_stale)
    results = load_stale_inits(resolved_stale)

    from soma_inits_upgrades.phase_orchestration import run_all_phases
    run_all_phases(
        global_state, global_state_path,
        resolved_stale, resolved_output, state_dir, results, run_fn,
    )
