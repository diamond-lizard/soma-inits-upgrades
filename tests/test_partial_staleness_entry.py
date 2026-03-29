"""Tests for partial staleness: entry-level outcomes."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from runner_helpers import make_ctx, tracking_handler
from runner_patch_helpers import (
    PATCH_CC,
    PATCH_T1,
    PATCH_T2,
    PATCH_TC,
    log_clone_cleanup,
    log_temp_cleanup,
    ok_tier1,
)

from soma_inits_upgrades.processing_runner import run_entry_task_loop
from soma_inits_upgrades.state_schema import TIER_1_TASKS, TIER_2_TASKS, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_one_current_one_stale_entry_processed(tmp_path: Path) -> None:
    """(e) One repo current, one stale: entry is still processed."""
    r_current = RepoState(
        repo_url="https://github.com/o/current", pinned_ref="aaa",
    )
    r_current.done_reason = "already_latest"
    r_stale = RepoState(
        repo_url="https://github.com/o/stale", pinned_ref="bbb",
    )
    ctx = make_ctx(tmp_path, [r_current, r_stale])
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    for task in TIER_2_TASKS:
        assert task in log, f"Tier 2 task {task!r} should have run"
    assert ctx.entry_state.status != "error"


def test_all_repos_current_entry_skipped(tmp_path: Path) -> None:
    """(f) All repos current: Tier 2 does not run, entry is skipped."""
    r1 = RepoState(
        repo_url="https://github.com/o/a", pinned_ref="aaa",
    )
    r1.done_reason = "already_latest"
    r2 = RepoState(
        repo_url="https://github.com/o/b", pinned_ref="bbb",
    )
    r2.done_reason = "already_latest"
    ctx = make_ctx(tmp_path, [r1, r2])
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    for task in TIER_2_TASKS:
        assert task not in log, f"Tier 2 task {task!r} should NOT run"
