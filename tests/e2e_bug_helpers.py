"""Shared helpers for bug-fix end-to-end integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.state_schema import RepoState


def mark_all_tier1_done(repo: RepoState) -> None:
    """Mark every Tier 1 task complete on a RepoState."""
    for key in repo.tier1_tasks_completed:
        repo.tier1_tasks_completed[key] = True


def deps_handler_that_sets_name(name: str, log: list[str]):
    """Return a deps handler that sets package_name and logs."""
    def handler(repo_ctx):
        log.append(f"deps:{name}")
        repo_ctx.repo_state.package_name = name
        repo_ctx.repo_state.tier1_tasks_completed["deps"] = True
        return False
    return handler


def tier2_noop_handler(log: list[str], tag: str):
    """Tier 2 handler that marks complete and logs."""
    def handler(ctx):
        log.append(tag)
        ctx.entry_state.tasks_completed[tag] = True
        return False
    return handler
