"""Tests for partial staleness handling in the two-tier runner."""

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


def _make_partial_repos() -> tuple[RepoState, RepoState]:
    """Build one done repo and one active repo."""
    r_done = RepoState(
        repo_url="https://github.com/o/done", pinned_ref="aaa",
    )
    r_done.done_reason = "already_latest"
    r_active = RepoState(
        repo_url="https://github.com/o/active", pinned_ref="bbb",
    )
    return r_done, r_active


def test_partial_staleness_skips_done_runs_active(tmp_path: Path) -> None:
    """(a,b) Tier 1 skips done repos; Tier 2 runs with active repos."""
    r_done, r_active = _make_partial_repos()
    ctx = make_ctx(tmp_path, [r_done, r_active])
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    t1_entries = [
        e for e in log
        if ":" in e and e.split(":")[0] in TIER_1_TASKS
    ]
    assert all(e.endswith(":active") for e in t1_entries)
    assert not any(e.endswith(":done") for e in t1_entries)
    for task in TIER_2_TASKS:
        assert task in log, f"Tier 2 task {task!r} should have run"


def test_prompt_filters_done_repos(tmp_path: Path) -> None:
    """(c) Security review prompt excludes repos with done_reason."""
    from soma_inits_upgrades.entry_tasks_llm import task_security_review
    from soma_inits_upgrades.repo_utils import derive_repo_dir_name

    r_done, r_active = _make_partial_repos()
    ctx = make_ctx(tmp_path, [r_done, r_active])
    ctx.entry_state.status = "in_progress"
    for repo in ctx.entry_state.repos:
        rdir = ctx.tmp_dir / derive_repo_dir_name(repo.repo_url)
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / f"{ctx.init_stem}.diff").write_text("fake diff")
    captured: list[str] = []

    def fake_run_llm(_ctx, task_name, prompt_fn, _prompt_file,
                     _output_file, _prereqs, _heal_fn, _label):
        captured.append(prompt_fn())
        _ctx.entry_state.tasks_completed[task_name] = True
        return "continue"

    target = "soma_inits_upgrades.llm_task.run_llm_task"
    with patch(target, fake_run_llm):
        task_security_review(ctx)
    assert len(captured) == 1
    assert "o/active" in captured[0]
    assert "o/done" not in captured[0]
