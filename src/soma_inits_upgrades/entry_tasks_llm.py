"""LLM-driven entry tasks: security review and upgrade analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.prompts import SecurityRepoInfo
    from soma_inits_upgrades.prompts_upgrade import AnalysisRepoInfo
    from soma_inits_upgrades.protocols import EntryContext


def task_security_review(ctx: EntryContext) -> bool:
    """Run the security review LLM pause."""
    from soma_inits_upgrades.llm_task import run_llm_task
    from soma_inits_upgrades.processing_helpers import self_heal_entry_resource
    from soma_inits_upgrades.prompts import generate_security_review_prompt
    from soma_inits_upgrades.repo_utils import derive_repo_dir_name
    output = ctx.output_dir / f"{ctx.entry_state.init_file}-security-review.md"
    prompt = ctx.tmp_dir / f"{ctx.init_stem}-security-review.prompt.md"
    malformed = output.with_suffix(output.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    repos_info: list[SecurityRepoInfo] = []
    for repo in ctx.entry_state.repos:
        if repo.done_reason is not None:
            continue
        rdir = ctx.tmp_dir / derive_repo_dir_name(repo.repo_url)
        diff = rdir / f"{ctx.init_stem}.diff"
        if not diff.exists():
            continue
        repos_info.append({
            "package_name": repo.package_name or ctx.init_stem,
            "repo_url": repo.repo_url,
            "pinned_ref": repo.pinned_ref,
            "latest_ref": repo.latest_ref or "",
            "diff_path": diff,
        })
    def prompt_fn() -> str:
        return generate_security_review_prompt(
            repos_info, output, malformed_report_path=mal_arg,
        )
    return run_llm_task(
        ctx, "security_review", prompt_fn, prompt, output,
        [], self_heal_entry_resource, "Security Review",
    ) == "break"


def task_upgrade_analysis(ctx: EntryContext) -> bool:
    """Run the upgrade analysis LLM pause and validate output."""
    from soma_inits_upgrades.entry_tasks_dep_context import build_dep_context
    from soma_inits_upgrades.llm_task import run_llm_task
    from soma_inits_upgrades.output_validation import (
        validate_upgrade_analysis_output,
    )
    from soma_inits_upgrades.processing_helpers import self_heal_entry_resource
    from soma_inits_upgrades.prompts_upgrade import (
        generate_upgrade_analysis_prompt,
    )
    from soma_inits_upgrades.repo_utils import derive_repo_dir_name
    output = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.json"
    prompt = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.prompt.md"
    malformed = output.with_suffix(output.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    dep_ctx = build_dep_context(ctx)
    repos_info: list[AnalysisRepoInfo] = []
    for repo in ctx.entry_state.repos:
        if repo.done_reason is not None:
            continue
        rdir = ctx.tmp_dir / derive_repo_dir_name(repo.repo_url)
        diff = rdir / f"{ctx.init_stem}.diff"
        usage = rdir / f"{ctx.init_stem}-usage-analysis.json"
        if not usage.exists():
            continue
        repos_info.append({
            "package_name": repo.package_name or ctx.init_stem,
            "repo_url": repo.repo_url,
            "pinned_ref": repo.pinned_ref,
            "latest_ref": repo.latest_ref or "",
            "diff_path": diff,
            "usage_path": usage,
        })
    def prompt_fn() -> str:
        return generate_upgrade_analysis_prompt(
            repos_info, output, dep_ctx,
            malformed_analysis_path=mal_arg,
        )
    result = run_llm_task(
        ctx, "upgrade_analysis", prompt_fn, prompt, output,
        [], self_heal_entry_resource, "Upgrade Analysis",
    )
    if result == "break":
        return True
    is_done = ctx.entry_state.tasks_completed.get(
        "upgrade_analysis", False,
    )
    if is_done and not validate_upgrade_analysis_output(
        output, self_heal_entry_resource, ctx,
    ):
        ctx.entry_state.tasks_completed["upgrade_analysis"] = False
    return False
