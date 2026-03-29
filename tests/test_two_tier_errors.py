"""Tests for two-tier error handling and resumability."""

from __future__ import annotations

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
from soma_inits_upgrades.state_schema import (
    TIER_1_TASKS,
    TIER_2_TASKS,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import RepoContext



def test_tier1_failure_isolated_to_repo(tmp_path: Path) -> None:
    """Tier 1 error in repo 'a' does not prevent repo 'b'."""
    r1 = RepoState(repo_url="https://github.com/o/a", pinned_ref="a")
    r2 = RepoState(repo_url="https://github.com/o/b", pinned_ref="b")
    ctx = make_ctx(tmp_path, [r1, r2])
    log: list[str] = []
    t1 = {t: fail_tier1_on("diff", "a", log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, fake_cleanup),
    ):
        run_entry_task_loop(ctx)
    assert r1.done_reason == "error"
    assert r2.done_reason is None
    b_tasks = [e for e in log if e.endswith(":b")]
    assert len(b_tasks) == len(TIER_1_TASKS)


def test_done_early_no_progress_error(tmp_path: Path) -> None:
    """set_repo_done_early does not trigger 'no progress' error."""
    repo = RepoState(repo_url="https://github.com/o/r", pinned_ref="a")
    ctx = make_ctx(tmp_path, [repo])
    log: list[str] = []

    def latest_ref_skip(repo_ctx: RepoContext) -> bool:
        from soma_inits_upgrades.processing_helpers_repo import (
            set_repo_done_early,
        )
        log.append("latest_ref")
        set_repo_done_early(repo_ctx, "already_latest", "up to date")
        return False

    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t1["latest_ref"] = latest_ref_skip
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, fake_cleanup),
    ):
        run_entry_task_loop(ctx)
    assert repo.done_reason == "already_latest"
    assert "no progress" not in (repo.notes or "")


def test_resume_skips_done_repo(tmp_path: Path) -> None:
    """On resume, a repo with done_reason set is skipped entirely."""
    r1 = RepoState(
        repo_url="https://github.com/o/a", pinned_ref="a",
        done_reason="already_latest", notes="up to date",
    )
    r2 = RepoState(repo_url="https://github.com/o/b", pinned_ref="b")
    ctx = make_ctx(tmp_path, [r1, r2])
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, fake_cleanup),
    ):
        run_entry_task_loop(ctx)
    a_calls = [e for e in log if ":a" in e]
    assert a_calls == [], "repo 'a' should be skipped entirely"
    b_calls = [e for e in log if ":b" in e]
    assert len(b_calls) == len(TIER_1_TASKS)
