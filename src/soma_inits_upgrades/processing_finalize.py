"""Processing finalization: entry completion bookkeeping and cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def finalize_entry(ctx: EntryContext) -> None:
    """Post-loop cleanup and bookkeeping for a completed entry."""
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_artifacts import delete_entry_artifacts

    # Two-tier: aggregate repo done_reasons to entry level
    if ctx.entry_state.status not in ("done", "error"):
        _aggregate_repo_outcomes(ctx)

    status = ctx.entry_state.status
    cleanup_done = ctx.entry_state.tasks_completed.get("temp_cleanup", False)
    is_permanent_error = status == "error" and ctx.entry_state.retries_remaining == 0
    can_cleanup = status == "done" or is_permanent_error
    if not cleanup_done and can_cleanup:
        delete_entry_artifacts(
            ctx.entry_state.init_file, ctx.output_dir,
            include_permanent=False, include_temp=True,
        )
        ctx.entry_state.tasks_completed["temp_cleanup"] = True
        if status == "error":
            _cleanup_malformed(ctx)
            atomic_write_json(ctx.entry_state_path, ctx.entry_state)
            return
    if status == "error" and ctx.entry_state.retries_remaining == 0:
        _cleanup_malformed(ctx)
    if status != "error":
        from soma_inits_upgrades.processing_finalize_bookkeeping import complete_entry_bookkeeping
        complete_entry_bookkeeping(ctx)


def _aggregate_repo_outcomes(ctx: EntryContext) -> None:
    """Aggregate per-repo done_reasons into entry-level outcome."""
    from soma_inits_upgrades.processing_helpers import set_entry_error
    from soma_inits_upgrades.state_schema import TIER_2_TASKS

    repos = ctx.entry_state.repos
    errored = [r for r in repos if r.done_reason == "error"]
    if errored:
        active = [r for r in repos if r.done_reason is None]
        tier2_done = all(
            ctx.entry_state.tasks_completed.get(t, False)
            for t in TIER_2_TASKS
        )
        if active and tier2_done:
            failed = [r.repo_url for r in errored]
            ctx.entry_state.done_reason = "partial"
            ctx.entry_state.notes = f"Tier 1 failed for: {', '.join(failed)}"
            ctx.entry_state.status = "done"
        else:
            from soma_inits_upgrades.processing_finalize_prompt import (
                prompt_on_all_repos_errored,
            )
            set_entry_error(ctx, "no repo produced a usable diff")
            prompt_on_all_repos_errored(ctx)
        return
    if all(r.done_reason is not None for r in repos):
        reasons = {r.done_reason for r in repos}
        if reasons == {"already_latest"}:
            ctx.entry_state.done_reason = "already_latest"
        elif reasons == {"empty_diff"}:
            ctx.entry_state.done_reason = "empty_diff"
        else:
            ctx.entry_state.done_reason = "no_changes_needed"
        ctx.entry_state.status = "done"


def _cleanup_malformed(ctx: EntryContext) -> None:
    """Remove .malformed files for a permanently-errored entry."""
    from soma_inits_upgrades.output_validation_tasks import cleanup_malformed_files
    cleanup_malformed_files(ctx.output_dir, ctx.entry_state.init_file)

