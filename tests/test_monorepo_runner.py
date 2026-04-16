"""Integration test: _validate_repo_artifacts skips derived entries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from monorepo_test_helpers import make_el_with_header, make_monorepo_ctx
from runner_helpers import tracking_handler
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


def test_validate_skips_derived_entries(tmp_path: Path) -> None:
    """Full loop with security_review=True preserves derived entries.

    When security_review is complete _reset_tier1_on_restart exits
    early.  _validate_repo_artifacts then skips derived entries so
    their Tier 1 tasks and package_name remain intact.
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
    for k in ctx.entry_state.tasks_completed:
        ctx.entry_state.tasks_completed[k] = True
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    repos = ctx.entry_state.repos
    assert len(repos) == 2
    derived = next(r for r in repos if r.is_monorepo_derived)
    assert all(derived.tier1_tasks_completed.values())
    assert derived.package_name == "swiper"
    assert ctx.entry_state.multi_package_verified is True
