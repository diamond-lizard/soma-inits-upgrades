"""End-to-end resumability test (TASK-28400).

Simulates interruption after Setup completes, then resumes and
verifies the tool finishes all remaining stages without repeating
setup work.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from e2e_helpers import RESULTS, pre_create_llm_outputs, write_stale_json
from e2e_setup import make_fake_git_for_e2e, run_setup_phase

from soma_inits_upgrades.finalization import (
    dispatch_graph_finalization,
    dispatch_summary_stage,
)
from soma_inits_upgrades.phase_dispatch_run import (
    complete_entry_processing,
    run_entry_processing,
)
from soma_inits_upgrades.state import read_global_state

if TYPE_CHECKING:
    from pathlib import Path


def test_e2e_resumability(tmp_path: Path) -> None:
    """Interrupt after Setup, resume, and verify full completion."""
    stale_path = write_stale_json(tmp_path)
    _gs, gs_path = run_setup_phase(tmp_path, stale_path)
    output_dir = tmp_path / "output"
    state_dir = output_dir / ".state"

    # Simulate restart: re-read global state from disk
    gs2 = read_global_state(gs_path)
    assert gs2 is not None
    assert gs2.phases.setup == "done"
    assert gs2.phases.entry_processing == "pending"

    for entry in RESULTS:
        pre_create_llm_outputs(output_dir, entry["init_file"])

    fg = make_fake_git_for_e2e(output_dir / ".tmp")
    needs_rerun = run_entry_processing(
        RESULTS, state_dir, output_dir, gs2, fg,
        input_fn=lambda _: "c",
    )
    complete_entry_processing(gs2, state_dir, needs_rerun)
    assert gs2.phases.entry_processing == "done"

    dispatch_graph_finalization(gs2, gs_path, output_dir)
    assert gs2.phases.graph_finalization == "done"

    dispatch_summary_stage(gs2, gs_path, output_dir)
    assert gs2.completed is True

    # Verify persisted state matches
    final = read_global_state(gs_path)
    assert final is not None
    assert final.completed is True
