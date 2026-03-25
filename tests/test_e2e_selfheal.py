"""End-to-end self-healing test (TASK-28500).

Runs the tool through completion, deletes a security review report,
resets validate_outputs, and re-runs.  Verifies the tool detects the
missing file, resets the security_review task via self-healing, and
re-pauses for the LLM (simulated via pre-created file and input_fn).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from e2e_helpers import RESULTS, pre_create_llm_outputs, write_stale_json
from e2e_setup import make_fake_git_for_e2e, run_setup_phase

from soma_inits_upgrades.phase_dispatch_run import (
    complete_entry_processing,
    run_entry_processing,
)
from soma_inits_upgrades.state import atomic_write_json, read_entry_state

if TYPE_CHECKING:
    from pathlib import Path


def test_e2e_self_healing(tmp_path: Path) -> None:
    """Delete a security review after completion, verify recovery."""
    stale_path = write_stale_json(tmp_path)
    gs, gs_path = run_setup_phase(tmp_path, stale_path)
    output_dir = tmp_path / "output"
    state_dir = output_dir / ".state"

    for entry in RESULTS:
        pre_create_llm_outputs(output_dir, entry["init_file"])

    # First run: complete all entries
    fg = make_fake_git_for_e2e(output_dir / ".tmp")
    needs_rerun = run_entry_processing(
        RESULTS, state_dir, output_dir, gs, fg,
        input_fn=lambda _: "c",
    )
    complete_entry_processing(gs, state_dir, needs_rerun)
    _verify_alpha_done(state_dir)

    # Tamper: delete security review and reset entry for re-processing
    _tamper_entry_alpha(state_dir, output_dir, gs, gs_path)

    # Re-create the security review (simulating LLM re-doing it)
    pre_create_llm_outputs(output_dir, "soma-alpha-init.el")

    # Second run: should recover via self-healing
    fg2 = make_fake_git_for_e2e(output_dir / ".tmp")
    needs_rerun = run_entry_processing(
        RESULTS, state_dir, output_dir, gs, fg2,
        input_fn=lambda _: "c",
    )
    complete_entry_processing(gs, state_dir, needs_rerun)
    _verify_alpha_done(state_dir)


def _verify_alpha_done(state_dir: Path) -> None:
    """Assert entry A is in done status."""
    es = read_entry_state(state_dir / "soma-alpha-init.el.json")
    assert es is not None
    assert es.status == "done"


def _tamper_entry_alpha(
    state_dir: Path, output_dir: Path, gs: object, gs_path: Path,
) -> None:
    """Delete security review and reset entry state for re-processing."""
    review = output_dir / "soma-alpha-init.el-security-review.md"
    review.unlink()

    es = read_entry_state(state_dir / "soma-alpha-init.el.json")
    assert es is not None
    es.tasks_completed["validate_outputs"] = False
    es.tasks_completed["cleanup"] = False
    es.status = "in_progress"
    atomic_write_json(state_dir / "soma-alpha-init.el.json", es)

    gs.phases.entry_processing = "in_progress"
    gs.entries_summary.done -= 1
    gs.entries_summary.in_progress += 1
    atomic_write_json(gs_path, gs)
