"""Dependency context builder for upgrade and report prompts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def build_dep_context(ctx: EntryContext) -> str:
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
