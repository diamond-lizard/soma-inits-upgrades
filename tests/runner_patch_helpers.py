"""Patch targets and logging helpers for two-tier runner tests."""

from __future__ import annotations

from runner_helpers import fake_cleanup

PATCH_T1 = "soma_inits_upgrades.processing.TIER_1_HANDLERS"
PATCH_T2 = "soma_inits_upgrades.processing.TIER_2_HANDLERS"
PATCH_CC = "soma_inits_upgrades.processing_runner.clone_cleanup"
PATCH_TC = "soma_inits_upgrades.processing_runner.task_temp_cleanup"


def noop_clone_cleanup(_repo_ctx: object) -> None:
    """No-op clone cleanup for tests."""


def log_temp_cleanup(log: list[str]):
    """Return a temp cleanup handler that appends to the log."""
    def handler(ctx):
        log.append("temp_cleanup")
        return fake_cleanup(ctx)
    return handler


def log_clone_cleanup(log: list[str]):
    """Return a clone cleanup handler that appends to the log."""
    def handler(repo_ctx):
        url = repo_ctx.repo_state.repo_url.split("/")[-1]
        log.append(f"clone_cleanup:{url}")
    return handler


def ok_tier1(log: list[str], tag: str):
    """Tier 1 handler that succeeds and logs repo name."""
    def handler(repo_ctx):
        url = repo_ctx.repo_state.repo_url.split("/")[-1]
        log.append(f"{tag}:{url}")
        repo_ctx.repo_state.tier1_tasks_completed[tag] = True
        return False
    return handler


def fail_tier1_on(fail_task: str, fail_repo: str, log: list[str], tag: str):
    """Tier 1 handler that raises on a specific task+repo combo."""
    def handler(repo_ctx):
        url = repo_ctx.repo_state.repo_url.split("/")[-1]
        log.append(f"{tag}:{url}")
        if tag == fail_task and url == fail_repo:
            raise RuntimeError(f"boom in {tag}")
        repo_ctx.repo_state.tier1_tasks_completed[tag] = True
        return False
    return handler
