"""End-to-end test: full lifecycle through all four stages (TASK-28300)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from e2e_helpers import RESULTS, pre_create_llm_outputs, write_stale_json
from e2e_setup import make_fake_git_for_e2e, run_setup_phase

from soma_inits_upgrades.finalization import (
    dispatch_graph_finalization,
    dispatch_summary_stage,
)
from soma_inits_upgrades.graph import read_graph
from soma_inits_upgrades.phase_dispatch_run import (
    complete_entry_processing,
    run_entry_processing,
)
from soma_inits_upgrades.state import read_entry_state, read_global_state

if TYPE_CHECKING:
    from pathlib import Path


def test_e2e_full_lifecycle(tmp_path: Path) -> None:
    """Run all four stages end-to-end and verify final state."""
    stale_path = write_stale_json(tmp_path)
    gs, gs_path = run_setup_phase(tmp_path, stale_path)
    output_dir = tmp_path / "output"
    state_dir = output_dir / ".state"

    _verify_setup(gs, state_dir, output_dir)

    for entry in RESULTS:
        pre_create_llm_outputs(output_dir, entry["init_file"])

    fg = make_fake_git_for_e2e(output_dir / ".tmp")
    needs_rerun = run_entry_processing(
        RESULTS, state_dir, output_dir, gs, fg,
        input_fn=lambda _: "c",
    )
    complete_entry_processing(gs, state_dir, needs_rerun)
    _verify_entry_processing(gs, state_dir, needs_rerun)

    dispatch_graph_finalization(gs, gs_path, output_dir)
    _verify_graph_finalization(gs, output_dir)

    dispatch_summary_stage(gs, gs_path, output_dir, start_time=None)
    _verify_summary(gs, gs_path, output_dir)


def _verify_setup(gs: object, state_dir: Path, output_dir: Path) -> None:
    """Check Setup stage created expected artifacts."""
    assert gs.phases.setup == "done"
    assert (state_dir / "soma-alpha-init.el.json").is_file()
    assert (state_dir / "soma-beta-init.el.json").is_file()
    assert (output_dir / "soma-inits-dependency-graphs.json").is_file()
    assert gs.emacs_version == "29.1"
    assert len(gs.entry_names) == 2


def _verify_entry_processing(
    gs: object, state_dir: Path, needs_rerun: bool,
) -> None:
    """Check Per-Entry Processing completed both entries."""
    assert gs.phases.entry_processing == "done"
    assert not needs_rerun
    for entry in RESULTS:
        es = read_entry_state(state_dir / f"{entry['init_file']}.json")
        assert es is not None
        assert es.status == "done", f"{entry['init_file']}: {es.status} / {es.notes}"
        assert es.package_name is not None


def _verify_graph_finalization(gs: object, output_dir: Path) -> None:
    """Check Graph Finalization populated depended_on_by."""
    assert gs.phases.graph_finalization == "done"
    graph, _ = read_graph(output_dir / "soma-inits-dependency-graphs.json")
    assert "soma-alpha-init.el" in graph
    assert "soma-beta-init.el" in graph


def _verify_summary(gs: object, gs_path: Path, output_dir: Path) -> None:
    """Check Summary stage wrote reports and marked completion."""
    assert gs.phases.summary == "done"
    assert gs.completed is True
    assert (output_dir / "security-review-summary.md").is_file()
    # emacs-version-conflicts.md only created when conflicts exist
    final_gs = read_global_state(gs_path)
    assert final_gs is not None
    assert final_gs.completed is True
    assert final_gs.date_completed is not None
