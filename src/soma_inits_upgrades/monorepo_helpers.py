"""Low-level helpers for monorepo multi-package metadata extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.deps_selection import PackageCandidate
    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state_schema import RepoState


def extract_raw_deps(candidate: PackageCandidate) -> str | None:
    """Extract raw dependency s-expression from a candidate.

    For pkg_el candidates, returns the pre-populated raw_deps.
    For header candidates, reads the file and extracts the header value.
    """
    if candidate.source_type == "pkg_el":
        return candidate.raw_deps
    from soma_inits_upgrades.deps_header_parsing import extract_multiline_requires

    lines = candidate.path.read_text(encoding="utf-8").splitlines()
    assert candidate.header_line is not None
    return extract_multiline_requires(lines, candidate.header_line - 1)


def parse_deps(raw_deps: str | None) -> tuple[list[str], str | None]:
    """Parse raw dependency s-expression into depends_on and min_emacs.

    Returns ([], None) when raw_deps is None.
    """
    if raw_deps is None:
        return [], None
    from soma_inits_upgrades.deps_processing import (
        filter_dependencies,
        parse_requirements_sexp,
    )

    parsed = parse_requirements_sexp(raw_deps)
    return filter_dependencies(parsed)


def persist_entry(ctx: EntryContext) -> None:
    """Persist the entry state to disk."""
    from soma_inits_upgrades.state import atomic_write_json

    atomic_write_json(ctx.entry_state_path, ctx.entry_state)


def create_derived_repo_state(
    candidate: PackageCandidate,
    original: RepoState,
    emacs_version: str,
) -> RepoState:
    """Build a fully-populated derived RepoState for a monorepo package."""
    from soma_inits_upgrades.deps_resolution import requires_newer_emacs
    from soma_inits_upgrades.state_schema import RepoState

    raw_deps = extract_raw_deps(candidate)
    depends_on, min_emacs = parse_deps(raw_deps)
    derived = RepoState(
        repo_url=original.repo_url,
        pinned_ref=original.pinned_ref,
        latest_ref=original.latest_ref,
        default_branch=original.default_branch,
        package_name=candidate.stem,
        depends_on=depends_on,
        min_emacs_version=min_emacs,
        emacs_upgrade_required=requires_newer_emacs(min_emacs, emacs_version),
        is_monorepo_derived=True,
    )
    for key in derived.tier1_tasks_completed:
        derived.tier1_tasks_completed[key] = True
    return derived
