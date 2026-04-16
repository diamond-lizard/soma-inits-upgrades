"""Tests for security review enforcement in task_upgrade_report."""

from __future__ import annotations

from typing import TYPE_CHECKING

from runner_helpers import make_ctx

from soma_inits_upgrades.entry_tasks_report import task_upgrade_report
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path

_REPO = RepoState(repo_url="https://forge.test/r", pinned_ref="a")


def test_upgrade_report_proceeds_when_security_review_exists(
    tmp_path: Path,
) -> None:
    """(a) Security review exists -- proceeds past it to analysis prereq.

    The analysis file is deliberately missing with its task marked
    complete, so self_heal_entry_resource resets upgrade_analysis and
    returns early.  This proves the security review prereq passed
    (file existed, no self-heal) and execution reached the next
    prerequisite -- all exercised through the real DI chain with
    zero mocking.
    """
    ctx = make_ctx(tmp_path, [_REPO])
    sr = ctx.output_dir / f"{ctx.entry_state.init_file}-security-review.md"
    sr.write_text("# Security Review\n")
    ctx.entry_state.tasks_completed["upgrade_analysis"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    result = task_upgrade_report(ctx)
    assert not result
    assert not ctx.entry_state.tasks_completed["upgrade_analysis"]


def test_upgrade_report_self_heals_missing_security_review(
    tmp_path: Path,
) -> None:
    """(b) Security review missing, task complete -- self-heal resets."""
    ctx = make_ctx(tmp_path, [_REPO])
    ctx.entry_state.tasks_completed["security_review"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    result = task_upgrade_report(ctx)
    assert not result
    assert not ctx.entry_state.tasks_completed["security_review"]


def test_upgrade_report_proceeds_when_review_task_incomplete(
    tmp_path: Path,
) -> None:
    """(c) Security review missing, task not complete -- proceeds.

    Architecturally unreachable: find_next_tier2_task enforces ordering
    so security_review completes before upgrade_report is called.
    The analysis prereq trap (marked complete, file missing) proves
    execution passed the security review prereq without self-healing.
    """
    ctx = make_ctx(tmp_path, [_REPO])
    assert not ctx.entry_state.tasks_completed.get(
        "security_review", False,
    )
    ctx.entry_state.tasks_completed["upgrade_analysis"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    result = task_upgrade_report(ctx)
    assert not result
    assert not ctx.entry_state.tasks_completed["upgrade_analysis"]
