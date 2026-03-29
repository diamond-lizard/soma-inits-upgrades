"""Tests for two-tier task execution order in the entry task runner."""

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
from soma_inits_upgrades.state_schema import (
    TIER_1_TASKS,
    TIER_2_TASKS,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_single_repo_execution_order(tmp_path: Path) -> None:
    """With one repo: all Tier 1, clone_cleanup, Tier 2, temp_cleanup."""
    repo = RepoState(
        repo_url="https://github.com/o/r", pinned_ref="aaa",
    )
    ctx = make_ctx(tmp_path, [repo])
    log: list[str] = []
    t1 = {t: tracking_handler(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    expected = [
        *TIER_1_TASKS,
        "clone_cleanup:r",
        *TIER_2_TASKS,
        "temp_cleanup",
    ]
    assert log == expected


def test_tier1_per_repo_order(tmp_path: Path) -> None:
    """Tier 1 tasks execute for each repo, then Tier 2 once."""
    r1 = RepoState(
        repo_url="https://github.com/o/a", pinned_ref="aaa",
    )
    r2 = RepoState(
        repo_url="https://github.com/o/b", pinned_ref="bbb",
    )
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
    t1_a = [f"{t}:a" for t in TIER_1_TASKS]
    t1_b = [f"{t}:b" for t in TIER_1_TASKS]
    expected = [
        *t1_a, "clone_cleanup:a",
        *t1_b, "clone_cleanup:b",
        *TIER_2_TASKS,
        "temp_cleanup",
    ]
    assert log == expected
