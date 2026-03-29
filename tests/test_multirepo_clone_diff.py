"""Integration: two-repo init file clone and diff verification."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from fakes import make_fake_git
from multirepo_helpers import (
    DIR_A,
    DIR_B,
    INIT_STEM,
    noop_temp_cleanup,
    pre_create_llm_outputs,
    setup_two_repo,
)
from runner_patch_helpers import PATCH_CC, PATCH_TC, noop_clone_cleanup

from soma_inits_upgrades.processing_entry import process_single_entry

if TYPE_CHECKING:
    from pathlib import Path


def test_two_repo_clone_dirs(tmp_path: Path) -> None:
    """Two-repo entry creates two clone directories with org--repo naming."""
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
    assert (tmp_dir / DIR_A / "clone").is_dir()
    assert (tmp_dir / DIR_B / "clone").is_dir()


def test_two_repo_diff_files(tmp_path: Path) -> None:
    """Two-repo entry produces diff files in per-repo subdirectories."""
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
    diff_a = tmp_dir / DIR_A / f"{INIT_STEM}.diff"
    diff_b = tmp_dir / DIR_B / f"{INIT_STEM}.diff"
    assert diff_a.exists(), f"Missing diff for repo A: {diff_a}"
    assert diff_b.exists(), f"Missing diff for repo B: {diff_b}"
    assert diff_a.read_text(encoding="utf-8").strip()
    assert diff_b.read_text(encoding="utf-8").strip()
