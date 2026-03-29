"""Tests for two-tier task execution order in the entry task runner."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from runner_helpers import fake_cleanup, make_ctx, tracking_handler

from soma_inits_upgrades.processing_runner import run_entry_task_loop
from soma_inits_upgrades.state_schema import (
    TIER_1_TASKS,
    TIER_2_TASKS,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import RepoContext

_PATCHES = (
    "soma_inits_upgrades.processing.TIER_1_HANDLERS",
    "soma_inits_upgrades.processing.TIER_2_HANDLERS",
    "soma_inits_upgrades.processing_runner.task_cleanup",
)


def _log_cleanup(log: list[str]):
    """Return a cleanup handler that appends to the log."""
    def handler(ctx):
        log.append("cleanup")
        return fake_cleanup(ctx)
    return handler


def _repo_t1_handler(log: list[str], tag: str):
    """Tier 1 handler that includes repo name in log."""
    def handler(repo_ctx: RepoContext) -> bool:
        url = repo_ctx.repo_state.repo_url.split("/")[-1]
        log.append(f"{tag}:{url}")
        repo_ctx.repo_state.tier1_tasks_completed[tag] = True
        return False
    return handler


def test_single_repo_execution_order(tmp_path: Path) -> None:
    """With one repo: all Tier 1, then Tier 2, then cleanup."""
    repo = RepoState(repo_url="https://github.com/o/r", pinned_ref="aaa")
    ctx = make_ctx(tmp_path, [repo])
    log: list[str] = []
    t1 = {t: tracking_handler(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(_PATCHES[0], t1),
        patch(_PATCHES[1], t2),
        patch(_PATCHES[2], _log_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    expected = list(TIER_1_TASKS) + list(TIER_2_TASKS) + ["cleanup"]
    assert log == expected


def test_tier1_runs_per_repo_in_order(tmp_path: Path) -> None:
    """Tier 1 tasks execute for each repo, then Tier 2 once."""
    r1 = RepoState(repo_url="https://github.com/o/a", pinned_ref="aaa")
    r2 = RepoState(repo_url="https://github.com/o/b", pinned_ref="bbb")
    ctx = make_ctx(tmp_path, [r1, r2])
    log: list[str] = []
    t1 = {t: _repo_t1_handler(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(_PATCHES[0], t1),
        patch(_PATCHES[1], t2),
        patch(_PATCHES[2], _log_cleanup(log)),
    ):
        run_entry_task_loop(ctx)
    t1_a = [f"{t}:a" for t in TIER_1_TASKS]
    t1_b = [f"{t}:b" for t in TIER_1_TASKS]
    assert log == t1_a + t1_b + list(TIER_2_TASKS) + ["cleanup"]


def test_tier2_called_once_not_per_repo(tmp_path: Path) -> None:
    """Tier 2 tasks run exactly once regardless of repo count."""
    r1 = RepoState(repo_url="https://github.com/o/a", pinned_ref="aaa")
    r2 = RepoState(repo_url="https://github.com/o/b", pinned_ref="bbb")
    ctx = make_ctx(tmp_path, [r1, r2])
    log: list[str] = []
    t1 = {t: _repo_t1_handler(log, t) for t in TIER_1_TASKS}
    t2 = {t: tracking_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(_PATCHES[0], t1),
        patch(_PATCHES[1], t2),
        patch(_PATCHES[2], fake_cleanup),
    ):
        run_entry_task_loop(ctx)
    for task in TIER_2_TASKS:
        assert log.count(task) == 1
