"""Tests for repo-level self-healing exhaustion."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from runner_helpers import make_ctx

from soma_inits_upgrades.processing_helpers_repo import (
    self_heal_repo_resource,
)
from soma_inits_upgrades.protocols import RepoContext
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_repo_self_heal_limit_exceeded(tmp_path: Path) -> None:
    """SystemExit raised when repo self-healing limit reached."""
    repo = RepoState(repo_url="https://forge.test/r", pinned_ref="a")
    repo.tier1_tasks_completed["clone"] = True
    ctx = make_ctx(tmp_path, [repo])
    repo_temp = tmp_path / ".tmp" / "r"
    repo_temp.mkdir(parents=True)
    clone_dir = repo_temp / "clone"
    repo_ctx = RepoContext(
        entry_ctx=ctx,
        repo_state=repo,
        temp_dir=repo_temp,
        clone_dir=clone_dir,
    )
    repo_ctx.reset_counters["clone"] = 4
    with pytest.raises(SystemExit):
        self_heal_repo_resource(tmp_path / "gone.txt", "clone", repo_ctx)
    assert repo_ctx.repo_state.done_reason == "error"
    assert "self-healing limit" in (repo_ctx.repo_state.notes or "")
