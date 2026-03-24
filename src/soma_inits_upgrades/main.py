"""Click CLI definition for soma-inits-upgrades."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState


@click.command()
@click.argument("stale_inits_file", type=click.Path(exists=False))
@click.option(
    "--output-dir",
    default="~/.emacs.d/soma/inits-upgrades/",
    help="Output directory for reports and state.",
)
def cli(stale_inits_file: str, output_dir: str) -> None:
    """Automate security review and upgrade planning for stale elpaca pins."""

    from soma_inits_upgrades.cli_helpers import (
        check_stale_inits_mismatch,
        load_stale_inits,
        resolve_and_validate_paths,
    )
    from soma_inits_upgrades.process_lock import acquire_process_lock
    from soma_inits_upgrades.state import read_global_state

    resolved_stale, resolved_output = resolve_and_validate_paths(
        stale_inits_file, output_dir,
    )
    state_dir = resolved_output / ".state"
    global_state_path = state_dir / "global.json"

    _lock_fd = acquire_process_lock(state_dir)
    global_state = read_global_state(global_state_path)
    check_stale_inits_mismatch(global_state, resolved_stale)
    results = load_stale_inits(resolved_stale)

    if global_state is None or global_state.phases.setup != "done":
        _run_setup(
            global_state, global_state_path,
            resolved_stale, resolved_output, state_dir, results,
        )


def _run_setup(
    global_state: GlobalState | None,
    global_state_path: Path,
    resolved_stale: Path,
    resolved_output: Path,
    state_dir: Path,
    results: list[dict[str, str]],
) -> None:
    """Execute the Setup stage."""
    from soma_inits_upgrades.setup_completion import (
        complete_setup,
        initialize_dep_graph,
        initialize_entry_states,
    )
    from soma_inits_upgrades.setup_stage import (
        create_tmp_directory,
        initialize_global_state,
        prompt_emacs_version,
    )

    graph_path = resolved_output / "soma-inits-dependency-graphs.json"
    gs = initialize_global_state(global_state, global_state_path, resolved_stale)
    prompt_emacs_version(gs, global_state_path)
    create_tmp_directory(resolved_output)
    initialize_entry_states(results, state_dir, resolved_output, gs)
    initialize_dep_graph(graph_path)
    complete_setup(gs, global_state_path, results)
