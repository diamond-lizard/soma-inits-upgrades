"""Tests for _reset_tier1_on_restart: multi-repo scenarios."""

from __future__ import annotations

from typing import TYPE_CHECKING

from runner_helpers import make_ctx

from soma_inits_upgrades.processing_runner import (
    _reset_tier1_on_restart,
)
from soma_inits_upgrades.state import read_entry_state
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _all_done_repo(url: str = "https://forge.test/r") -> RepoState:
    """Build a RepoState with all Tier 1 tasks marked complete."""
    rs = RepoState(
        repo_url=url,
        pinned_ref="abc123",
        package_name="my-pkg",
    )
    for key in rs.tier1_tasks_completed:
        rs.tier1_tasks_completed[key] = True
    return rs


def test_restart_resets_multiple_repos(
    tmp_path: Path,
) -> None:
    """Multiple repos with all tier1 done are all reset."""
    rs1 = _all_done_repo("https://forge.test/r1")
    rs2 = _all_done_repo("https://forge.test/r2")
    ctx = make_ctx(tmp_path, repos=[rs1, rs2])
    _reset_tier1_on_restart(ctx)
    for rs in (rs1, rs2):
        assert all(
            v is False
            for v in rs.tier1_tasks_completed.values()
        )
        assert rs.package_name is None
    reloaded = read_entry_state(ctx.entry_state_path)
    assert reloaded is not None
    for rr in reloaded.repos:
        assert all(
            v is False
            for v in rr.tier1_tasks_completed.values()
        )
        assert rr.package_name is None
