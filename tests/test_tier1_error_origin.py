"""Test that Tier 1 error notes include exception origin info."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from unittest.mock import patch

from runner_helpers import fake_cleanup, make_ctx, tracking_handler
from runner_patch_helpers import (
    PATCH_CC,
    PATCH_T1,
    PATCH_T2,
    PATCH_TC,
    fail_tier1_on,
    noop_clone_cleanup,
    ok_tier1,
)

from soma_inits_upgrades.processing_runner import run_entry_task_loop
from soma_inits_upgrades.state_schema import TIER_1_TASKS, TIER_2_TASKS, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_tier1_error_includes_origin(tmp_path: Path) -> None:
    """Error notes include origin file, line, and function name."""
    repo = RepoState(repo_url="https://github.com/o/a", pinned_ref="a")
    ctx = make_ctx(tmp_path, [repo])
    log: list[str] = []
    t1 = {t: fail_tier1_on("diff", "a", log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, fake_cleanup),
    ):
        run_entry_task_loop(ctx)
    assert repo.done_reason == "error"
    assert repo.notes is not None
    assert re.search(
        r"\[origin: \w+\.py:\d+ in \w+\]$", repo.notes,
    )


def test_handler_internal_catch_includes_origin(tmp_path: Path) -> None:
    """Origin captured when handler catches exception and calls set_repo_error."""
    from soma_inits_upgrades.processing_helpers_repo import set_repo_error
    repo = RepoState(repo_url="https://github.com/o/a", pinned_ref="a")
    ctx = make_ctx(tmp_path, [repo])
    log: list[str] = []

    def catching_handler(repo_ctx):
        log.append("diff:a")
        try:
            raise RuntimeError("boom in diff")
        except Exception as exc:
            set_repo_error(repo_ctx, f"diff failed: {exc}", exc)
            return False

    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t1["diff"] = catching_handler
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, fake_cleanup),
    ):
        run_entry_task_loop(ctx)
    assert repo.done_reason == "error"
    assert repo.notes is not None
    assert re.search(
        r"\[origin: \w+\.py:\d+ in \w+\]$", repo.notes,
    )
