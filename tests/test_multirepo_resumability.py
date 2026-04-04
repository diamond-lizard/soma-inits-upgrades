"""Integration: multi-repo resumability after interruption."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from multirepo_helpers import (
    PIN_A,
    PIN_B,
    URL_A,
    URL_B,
    pre_create_llm_outputs,
)
from runner_helpers import tracking_handler
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


def _make_resumed_ctx(tmp_path: Path):
    """Build a context simulating resume after repo A completed Tier 1."""
    from runner_helpers import make_ctx

    r_a = RepoState(repo_url=URL_A, pinned_ref=PIN_A)
    for t in TIER_1_TASKS:
        r_a.tier1_tasks_completed[t] = True
    r_b = RepoState(repo_url=URL_B, pinned_ref=PIN_B)
    ctx = make_ctx(tmp_path, [r_a, r_b])
    repo_temp_a = ctx.tmp_dir / "alpha--outshine"
    repo_temp_a.mkdir(parents=True)
    ctx.entry_state.tasks_completed["security_review"] = True
    return ctx


def test_resume_skips_completed_repo(tmp_path: Path) -> None:
    """On resume, first repo's Tier 1 tasks are not re-executed."""
    ctx = _make_resumed_ctx(tmp_path)
    pre_create_llm_outputs(tmp_path)
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    repo_a_tasks = [e for e in log if e.endswith(":outshine")]
    assert "clone_cleanup:outshine" in log
    tier1_a = [e for e in repo_a_tasks if not e.startswith("clone_cleanup")]
    assert tier1_a == [], f"Repo A re-executed Tier 1 tasks: {tier1_a}"


def test_resume_runs_second_repo_tier1(tmp_path: Path) -> None:
    """On resume, second repo runs all Tier 1 tasks."""
    ctx = _make_resumed_ctx(tmp_path)
    pre_create_llm_outputs(tmp_path)
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    expected_b = [f"{t}:outorg" for t in TIER_1_TASKS]
    tier1_b = [e for e in log if any(e == f"{t}:outorg" for t in TIER_1_TASKS)]
    assert tier1_b == expected_b


def test_resume_runs_tier2_after_both_repos(tmp_path: Path) -> None:
    """On resume, Tier 2 tasks run after both repos complete Tier 1."""
    ctx = _make_resumed_ctx(tmp_path)
    pre_create_llm_outputs(tmp_path)
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(PATCH_T1, t1), patch(PATCH_T2, t2),
        patch(PATCH_CC, log_clone_cleanup(log)),
        patch(PATCH_TC, log_temp_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    remaining = [t for t in TIER_2_TASKS if t != "security_review"]
    for tier2_task in remaining:
        assert tier2_task in log, f"Tier 2 task {tier2_task} not executed"
