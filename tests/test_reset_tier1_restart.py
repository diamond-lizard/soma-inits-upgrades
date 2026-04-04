"""Tests for _reset_tier1_on_restart: reset Tier 1 on restart."""

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


def test_restart_resets_when_all_tier1_done_security_not_done(
    tmp_path: Path,
) -> None:
    """All tier1 done + security_review not done resets tasks."""
    rs = _all_done_repo()
    ctx = make_ctx(tmp_path, repos=[rs])
    _reset_tier1_on_restart(ctx)
    assert all(
        v is False for v in rs.tier1_tasks_completed.values()
    )
    assert rs.package_name is None
    reloaded = read_entry_state(ctx.entry_state_path)
    assert reloaded is not None
    rr = reloaded.repos[0]
    assert all(
        v is False for v in rr.tier1_tasks_completed.values()
    )
    assert rr.package_name is None


def test_no_reset_when_security_review_done(
    tmp_path: Path,
) -> None:
    """Security review done means no Tier 1 reset."""
    rs = _all_done_repo()
    ctx = make_ctx(tmp_path, repos=[rs])
    ctx.entry_state.tasks_completed["security_review"] = True
    _reset_tier1_on_restart(ctx)
    assert all(
        v is True for v in rs.tier1_tasks_completed.values()
    )
    assert rs.package_name == "my-pkg"


def test_no_reset_when_tier1_partial(
    tmp_path: Path,
) -> None:
    """Partial tier1 done + security_review not done: no reset."""
    rs = RepoState(
        repo_url="https://forge.test/r",
        pinned_ref="abc123",
        package_name="my-pkg",
    )
    rs.tier1_tasks_completed["clone"] = True
    rs.tier1_tasks_completed["default_branch"] = True
    ctx = make_ctx(tmp_path, repos=[rs])
    _reset_tier1_on_restart(ctx)
    assert rs.tier1_tasks_completed["clone"] is True
    assert rs.tier1_tasks_completed["default_branch"] is True
    assert rs.package_name == "my-pkg"


def test_restart_skips_repos_with_done_reason(
    tmp_path: Path,
) -> None:
    """Repos with done_reason are not reset."""
    rs = _all_done_repo()
    rs.done_reason = "skipped"
    ctx = make_ctx(tmp_path, repos=[rs])
    _reset_tier1_on_restart(ctx)
    assert all(
        v is True for v in rs.tier1_tasks_completed.values()
    )
    assert rs.package_name == "my-pkg"
