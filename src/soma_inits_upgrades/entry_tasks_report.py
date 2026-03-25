"""Per-entry LLM task: upgrade report generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def task_upgrade_report(ctx: EntryContext) -> bool:
    """Run the upgrade report LLM pause."""
    from soma_inits_upgrades.entry_tasks_analysis import _build_dep_context
    from soma_inits_upgrades.llm_task import run_llm_task
    from soma_inits_upgrades.processing_helpers import self_heal_resource
    from soma_inits_upgrades.prompts_report import generate_upgrade_report_prompt

    name = ctx.entry_state.init_file
    analysis_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.json"
    output_path = ctx.output_dir / f"{name}-upgrade-process.md"
    prompt_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-report.prompt.md"
    malformed = output_path.with_suffix(output_path.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    dep_ctx = _build_dep_context(ctx)
    pkg = ctx.entry_state.package_name or ctx.init_stem

    def prompt_fn() -> str:
        """Generate the upgrade report prompt."""
        return generate_upgrade_report_prompt(
            pkg, ctx.entry_state.repo_url, ctx.entry_state.pinned_ref,
            ctx.entry_state.latest_ref or "", analysis_path,
            output_path, dep_ctx, malformed_report_path=mal_arg,
        )

    result = run_llm_task(
        ctx, "upgrade_report", prompt_fn, prompt_path, output_path,
        [(analysis_path, "upgrade_analysis")],
        self_heal_resource, "Upgrade Report",
    )
    return result == "break"
