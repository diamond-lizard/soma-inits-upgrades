"""Integration: two-repo init file produces one output file per artifact type."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from fakes import make_fake_git
from multirepo_helpers import (
    INIT_FILE,
    INIT_STEM,
    noop_temp_cleanup,
    pre_create_llm_outputs,
    setup_two_repo,
)
from runner_patch_helpers import PATCH_CC, PATCH_TC, noop_clone_cleanup

from soma_inits_upgrades.processing_entry import process_single_entry
from soma_inits_upgrades.state import read_entry_state

if TYPE_CHECKING:
    from pathlib import Path


def test_single_security_review(tmp_path: Path) -> None:
    """Two-repo entry produces exactly one security review file."""
    entry, gs, sd, gsp = setup_two_repo(tmp_path)
    pre_create_llm_outputs(tmp_path)
    fg = make_fake_git()
    with (
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, noop_temp_cleanup),
    ):
        process_single_entry(
            entry, 1, 1, sd, tmp_path, gs, gsp,
            fg, [entry], lambda: False, input_fn=lambda _: "c",
        )
    review_path = tmp_path / f"{INIT_FILE}-security-review.md"
    assert review_path.exists()
    matches = list(tmp_path.glob("*-security-review.md"))
    assert len(matches) == 1, f"Expected 1 security review, found {len(matches)}"


def test_single_upgrade_analysis(tmp_path: Path) -> None:
    """Two-repo entry produces exactly one upgrade analysis file."""
    entry, gs, sd, gsp = setup_two_repo(tmp_path)
    pre_create_llm_outputs(tmp_path)
    fg = make_fake_git()
    with (
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, noop_temp_cleanup),
    ):
        process_single_entry(
            entry, 1, 1, sd, tmp_path, gs, gsp,
            fg, [entry], lambda: False, input_fn=lambda _: "c",
        )
    tmp_dir = tmp_path / ".tmp" / INIT_STEM
    analysis = tmp_dir / f"{INIT_STEM}-upgrade-analysis.json"
    assert analysis.exists()


def test_single_upgrade_report(tmp_path: Path) -> None:
    """Two-repo entry produces exactly one upgrade report file."""
    entry, gs, sd, gsp = setup_two_repo(tmp_path)
    pre_create_llm_outputs(tmp_path)
    fg = make_fake_git()
    with (
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, noop_temp_cleanup),
    ):
        process_single_entry(
            entry, 1, 1, sd, tmp_path, gs, gsp,
            fg, [entry], lambda: False, input_fn=lambda _: "c",
        )
    report = tmp_path / f"{INIT_FILE}-upgrade-process.md"
    assert report.exists()
    matches = list(tmp_path.glob("*-upgrade-process.md"))
    assert len(matches) == 1, f"Expected 1 upgrade report, found {len(matches)}"


def test_entry_completes_done(tmp_path: Path) -> None:
    """Two-repo entry reaches done status after all tasks complete."""
    entry, gs, sd, gsp = setup_two_repo(tmp_path)
    pre_create_llm_outputs(tmp_path)
    fg = make_fake_git()
    with (
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, noop_temp_cleanup),
    ):
        process_single_entry(
            entry, 1, 1, sd, tmp_path, gs, gsp,
            fg, [entry], lambda: False, input_fn=lambda _: "c",
        )
    state = read_entry_state(sd / f"{INIT_FILE}.json")
    assert state is not None
    assert state.status == "done"
