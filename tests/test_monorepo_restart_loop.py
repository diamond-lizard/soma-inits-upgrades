"""Integration test: restart loop removes and recreates derived entries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from monorepo_test_helpers import make_el_with_header, make_monorepo_ctx
from runner_patch_helpers import (
    PATCH_CC,
    PATCH_T1,
    PATCH_T2,
    PATCH_TC,
    log_temp_cleanup,
    noop_clone_cleanup,
    ok_tier1,
)

from soma_inits_upgrades.entry_tasks_analysis import task_deps
from soma_inits_upgrades.processing_runner import run_entry_task_loop
from soma_inits_upgrades.state_schema import TIER_1_TASKS, TIER_2_TASKS

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import RepoContext


def _deps_handler(repo_ctx: RepoContext) -> bool:
    """Real deps handler for integration tests."""
    return task_deps(repo_ctx)


def _make_tier2_done(log: list[str]):
    """Build Tier 2 handlers that mark tasks complete and log."""
    from runner_helpers import tracking_handler
    return {t: tracking_handler(log, t) for t in TIER_2_TASKS}


def test_restart_removes_derived_and_recreates(tmp_path: Path) -> None:
    """Full loop: restart removes derived, re-runs deps, recreates them.

    After _reset_tier1_on_restart removes derived entries and resets
    Tier 1, the loop re-runs tier1 handlers.  The real task_deps
    handler triggers detect_monorepo_packages, which recreates the
    derived entries without duplicates.
    """
    repo_ctx = make_monorepo_ctx(
        tmp_path, "soma-ivy-init.el", ["ivy", "swiper"],
    )
    loop_clone = tmp_path / ".tmp" / "test--monorepo" / "clone"
    loop_clone.mkdir(parents=True)
    make_el_with_header(loop_clone, "ivy", '((emacs "25.1"))')
    make_el_with_header(loop_clone, "swiper", '((emacs "25.1"))')
    repo_ctx.clone_dir.mkdir(parents=True)
    make_el_with_header(repo_ctx.clone_dir, "ivy", '((emacs "25.1"))')
    make_el_with_header(repo_ctx.clone_dir, "swiper", '((emacs "25.1"))')
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    ctx = repo_ctx.entry_ctx
    assert len(ctx.entry_state.repos) == 2
    for r in ctx.entry_state.repos:
        for k in r.tier1_tasks_completed:
            r.tier1_tasks_completed[k] = True
    ctx.entry_state.tasks_completed["security_review"] = False
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t1["deps"] = _deps_handler
    t2 = _make_tier2_done(log)
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    repos = ctx.entry_state.repos
    assert len(repos) == 2
    derived = [r for r in repos if r.is_monorepo_derived]
    assert len(derived) == 1
    assert derived[0].package_name == "swiper"
    assert ctx.entry_state.multi_package_verified is True
    original = next(r for r in repos if not r.is_monorepo_derived)
    assert original.package_name is not None
