"""Per-entry analysis tasks: deps, version check, symbols, upgrade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext, RepoContext


def task_deps(repo_ctx: RepoContext) -> bool:
    """Parse dependency metadata from the cloned repository."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("deps", False):
        return False
    from soma_inits_upgrades.deps import locate_package_metadata
    from soma_inits_upgrades.deps_processing import (
        filter_dependencies,
        parse_requirements_sexp,
    )
    from soma_inits_upgrades.deps_resolution import determine_package_name
    from soma_inits_upgrades.git_ref_ops import ensure_working_tree_at_ref
    from soma_inits_upgrades.processing_helpers_repo import self_heal_repo_resource, set_repo_error
    from soma_inits_upgrades.state import mark_repo_task_complete
    ctx = repo_ctx.entry_ctx
    if self_heal_repo_resource(repo_ctx.clone_dir, "clone", repo_ctx):
        return False
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    eprint(f"{label} {ctx.entry_state.init_file}: parsing dependencies...")
    latest = repo_ctx.repo_state.latest_ref or ""
    if not ensure_working_tree_at_ref(repo_ctx.clone_dir, latest, run_fn=ctx.run_fn):
        msg = f"git checkout failed: latest_ref {repo_ctx.repo_state.latest_ref}"
        set_repo_error(repo_ctx, msg)
        return False
    raw_deps, pkg_name = locate_package_metadata(
        repo_ctx.clone_dir, init_file=ctx.entry_state.init_file,
        repo_url=repo_ctx.repo_state.repo_url, input_fn=ctx.input_fn,
    )
    depends_on: list[str] = []
    min_emacs: str | None = None
    if raw_deps:
        parsed = parse_requirements_sexp(raw_deps)
        depends_on, min_emacs = filter_dependencies(parsed)
    repo_ctx.repo_state.depends_on = depends_on
    repo_ctx.repo_state.min_emacs_version = min_emacs
    repo_ctx.repo_state.package_name = determine_package_name(
        pkg_name, ctx.entry_state.init_file,
    )
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state, "deps", ctx.entry_state_path,
    )
    return False


def task_version_check(repo_ctx: RepoContext) -> bool:
    """Compare minimum Emacs version requirement against user's version."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("version_check", False):
        return False
    from soma_inits_upgrades.deps_resolution import requires_newer_emacs
    from soma_inits_upgrades.state import mark_repo_task_complete
    ctx = repo_ctx.entry_ctx
    repo_ctx.repo_state.emacs_upgrade_required = requires_newer_emacs(
        repo_ctx.repo_state.min_emacs_version, ctx.global_state.emacs_version,
    )
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state,
        "version_check", ctx.entry_state_path,
    )
    return False



def _build_dep_context(ctx: EntryContext) -> str:
    """Build multi-repo dependency context string for upgrade prompts.

    For a single repo, returns output equivalent to the original format.
    For multiple repos, labels each repo's dependency section with the
    package name so the LLM can distinguish per-repo dependencies.
    """
    from soma_inits_upgrades.prompts_helpers import format_dependency_context
    repos = [r for r in ctx.entry_state.repos if r.done_reason is None]
    if len(repos) == 1:
        repo = repos[0]
        return format_dependency_context(
            repo.depends_on or [],
            repo.min_emacs_version,
            repo.emacs_upgrade_required,
            ctx.global_state.emacs_version,
        )
    parts: list[str] = []
    for repo in repos:
        label = repo.package_name or repo.repo_url
        section = format_dependency_context(
            repo.depends_on or [],
            repo.min_emacs_version,
            repo.emacs_upgrade_required,
            ctx.global_state.emacs_version,
        )
        parts.append(f"### {label}\n{section}")
    return "\n".join(parts) if parts else ""
