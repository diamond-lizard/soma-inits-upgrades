"""Per-entry LLM task: upgrade report generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.prompts_report import ReportRepoInfo
    from soma_inits_upgrades.protocols import EntryContext


def task_upgrade_report(ctx: EntryContext) -> bool:
    """Run the upgrade report LLM pause."""
    from soma_inits_upgrades.entry_tasks_dep_context import build_dep_context
    from soma_inits_upgrades.llm_task import run_llm_task
    from soma_inits_upgrades.processing_helpers import self_heal_entry_resource
    from soma_inits_upgrades.prompts_report import generate_upgrade_report_prompt
    name = ctx.entry_state.init_file
    analysis = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.json"
    security_review = ctx.output_dir / f"{name}-security-review.md"
    output = ctx.output_dir / f"{name}-upgrade-process.md"
    prompt = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-report.prompt.md"
    malformed = output.with_suffix(output.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    dep_ctx = build_dep_context(ctx)
    repos_info: list[ReportRepoInfo] = []
    for repo in ctx.entry_state.repos:
        if repo.done_reason is not None:
            continue
        repos_info.append({
            "package_name": repo.package_name or ctx.init_stem,
            "repo_url": repo.repo_url,
            "pinned_ref": repo.pinned_ref,
            "latest_ref": repo.latest_ref or "",
        })
    def prompt_fn() -> str:
        """Generate the upgrade report prompt."""
        return generate_upgrade_report_prompt(
            repos_info, analysis, output, dep_ctx,
            malformed_report_path=mal_arg,
        )
    result = run_llm_task(
        ctx, "upgrade_report", prompt_fn, prompt, output,
        [(security_review, "security_review"), (analysis, "upgrade_analysis")],
        self_heal_entry_resource, "Upgrade Report",
    )
    return result == "break"
