"""Tests for _validate_repo_artifacts: self-heal missing temp dir."""

from __future__ import annotations

from typing import TYPE_CHECKING

from runner_helpers import make_ctx

from soma_inits_upgrades.processing_runner import (
    _validate_repo_artifacts,
)
from soma_inits_upgrades.state import read_entry_state
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _all_done_repo() -> RepoState:
    """Build a RepoState with all Tier 1 tasks marked complete."""
    rs = RepoState(
        repo_url="https://forge.test/r",
        pinned_ref="abc123",
        package_name="my-pkg",
    )
    for key in rs.tier1_tasks_completed:
        rs.tier1_tasks_completed[key] = True
    return rs


def test_validate_all_done_temp_missing_resets(
    tmp_path: Path,
) -> None:
    """All tier1 done + missing temp dir resets tasks and package."""
    rs = _all_done_repo()
    ctx = make_ctx(tmp_path, repos=[rs])
    repo_temp = ctx.tmp_dir / "forge.test--r"
    _validate_repo_artifacts(
        rs, repo_temp, ctx.entry_state, ctx.entry_state_path,
    )
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


def test_validate_all_done_temp_exists_no_reset(
    tmp_path: Path,
) -> None:
    """All tier1 done + temp dir exists does not reset anything."""
    rs = _all_done_repo()
    ctx = make_ctx(tmp_path, repos=[rs])
    repo_temp = ctx.tmp_dir / "forge.test--r"
    repo_temp.mkdir(parents=True)
    _validate_repo_artifacts(
        rs, repo_temp, ctx.entry_state, ctx.entry_state_path,
    )
    assert all(
        v is True for v in rs.tier1_tasks_completed.values()
    )
    assert rs.package_name == "my-pkg"


def test_validate_partial_done_temp_missing_no_reset(
    tmp_path: Path,
) -> None:
    """Partial tier1 done + missing temp dir does not reset."""
    rs = RepoState(
        repo_url="https://forge.test/r",
        pinned_ref="abc123",
        package_name="my-pkg",
    )
    rs.tier1_tasks_completed["clone"] = True
    rs.tier1_tasks_completed["default_branch"] = True
    ctx = make_ctx(tmp_path, repos=[rs])
    repo_temp = ctx.tmp_dir / "forge.test--r"
    _validate_repo_artifacts(
        rs, repo_temp, ctx.entry_state, ctx.entry_state_path,
    )
    assert rs.tier1_tasks_completed["clone"] is True
    assert rs.tier1_tasks_completed["default_branch"] is True
    assert rs.package_name == "my-pkg"
