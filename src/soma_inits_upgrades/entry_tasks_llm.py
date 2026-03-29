"""LLM-driven entry tasks: security review and upgrade analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def task_security_review(ctx: EntryContext) -> bool:
    """Run the security review LLM pause."""
    from soma_inits_upgrades.llm_task import run_llm_task
    from soma_inits_upgrades.processing_helpers import self_heal_entry_resource
    from soma_inits_upgrades.prompts import generate_security_review_prompt
    name = ctx.entry_state.init_file
    diff_path = ctx.tmp_dir / f"{ctx.init_stem}.diff"
    output_path = ctx.output_dir / f"{name}-security-review.md"
    prompt_path = ctx.tmp_dir / f"{ctx.init_stem}-security-review.prompt.md"
    malformed = output_path.with_suffix(output_path.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    pkg = ctx.entry_state.repos[0].package_name or ctx.init_stem
    def prompt_fn() -> str:
        return generate_security_review_prompt(
            pkg, ctx.entry_state.repos[0].repo_url, ctx.entry_state.repos[0].pinned_ref,
            ctx.entry_state.repos[0].latest_ref or "", diff_path, output_path,
            malformed_report_path=mal_arg,
        )
    result = run_llm_task(
        ctx, "security_review", prompt_fn, prompt_path, output_path,
        [(diff_path, "diff")], self_heal_entry_resource, "Security Review",
    )
    return result == "break"


def task_upgrade_analysis(ctx: EntryContext) -> bool:
    """Run the upgrade analysis LLM pause and validate output."""
    from soma_inits_upgrades.entry_tasks_analysis import _build_dep_context
    from soma_inits_upgrades.llm_task import run_llm_task
    from soma_inits_upgrades.output_validation import validate_upgrade_analysis_output
    from soma_inits_upgrades.processing_helpers import self_heal_entry_resource
    from soma_inits_upgrades.prompts_upgrade import generate_upgrade_analysis_prompt
    diff_path = ctx.tmp_dir / f"{ctx.init_stem}.diff"
    usage_path = ctx.tmp_dir / f"{ctx.init_stem}-usage-analysis.json"
    output_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.json"
    prompt_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.prompt.md"
    malformed = output_path.with_suffix(output_path.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    dep_ctx = _build_dep_context(ctx)
    pkg = ctx.entry_state.repos[0].package_name or ctx.init_stem
    def prompt_fn() -> str:
        return generate_upgrade_analysis_prompt(
            pkg, ctx.entry_state.repos[0].repo_url, ctx.entry_state.repos[0].pinned_ref,
            ctx.entry_state.repos[0].latest_ref or "", diff_path, usage_path,
            output_path, dep_ctx, malformed_analysis_path=mal_arg,
        )
    result = run_llm_task(
        ctx, "upgrade_analysis", prompt_fn, prompt_path, output_path,
        [(diff_path, "diff"), (usage_path, "symbols")],
        self_heal_entry_resource, "Upgrade Analysis",
    )
    if result == "break":
        return True
    is_done = ctx.entry_state.tasks_completed.get("upgrade_analysis", False)
    if is_done and not validate_upgrade_analysis_output(
        output_path, self_heal_entry_resource, ctx,
    ):
        ctx.entry_state.tasks_completed["upgrade_analysis"] = False
    return False

