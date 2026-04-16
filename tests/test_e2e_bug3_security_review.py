"""E2E test: Bug 3 — security review enforcement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from runner_helpers import make_ctx

from soma_inits_upgrades.entry_tasks_report import task_upgrade_report
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path

_URL = "https://forge.test/r"


def test_missing_review_file_resets_task(tmp_path: Path) -> None:
    """Security review marked done but file missing triggers reset."""
    repo = RepoState(repo_url=_URL, pinned_ref="a")
    ctx = make_ctx(tmp_path, [repo])
    ctx.entry_state.tasks_completed["security_review"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    result = task_upgrade_report(ctx)
    assert not result
    assert not ctx.entry_state.tasks_completed["security_review"]
