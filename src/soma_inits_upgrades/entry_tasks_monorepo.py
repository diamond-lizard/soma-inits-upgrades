"""Monorepo multi-package detection for task_deps (Phase 400)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.deps_selection import PackageCandidate
    from soma_inits_upgrades.protocols import RepoContext
    from soma_inits_upgrades.state_schema import RepoState


def detect_monorepo_packages(repo_ctx: RepoContext) -> None:
    """Create derived RepoState entries for additional monorepo packages.

    After task_deps selects one package from a monorepo, this function
    checks whether the init file declares additional packages whose names
    match candidates in the repo's candidate pool.  For each match, a
    fully-populated RepoState is created with is_monorepo_derived=True
    and all Tier 1 tasks marked complete.
    """
    ctx = repo_ctx.entry_ctx
    if ctx.inits_dir is None:
        return
    init_path = ctx.inits_dir / ctx.entry_state.init_file
    declared = _get_declared_names(init_path)
    if not declared:
        ctx.entry_state.multi_package_verified = True
        return
    candidates = _build_pool(repo_ctx.clone_dir)
    extra = _find_extra_packages(declared, candidates, ctx.entry_state.repos)
    from soma_inits_upgrades.monorepo_helpers import create_derived_repo_state, persist_entry
    for cand in extra:
        derived = create_derived_repo_state(
            cand, repo_ctx.repo_state, ctx.global_state.emacs_version,
        )
        ctx.entry_state.repos.append(derived)
    ctx.entry_state.multi_package_verified = True
    persist_entry(ctx)


def _get_declared_names(init_path: object) -> list[str]:
    """Extract use-package names from the init file."""
    from soma_inits_upgrades.use_package_parser import extract_use_package_names

    return extract_use_package_names(init_path)  # type: ignore[arg-type]


def _build_pool(clone_dir: object) -> list[PackageCandidate]:
    """Build the candidate pool from the clone directory."""
    from soma_inits_upgrades.deps_candidate_pool import build_candidate_pool
    from soma_inits_upgrades.deps_finders import (
        find_package_requires_files,
        find_pkg_el_files,
    )

    pkg_files = find_pkg_el_files(clone_dir)  # type: ignore[arg-type]
    header_files = find_package_requires_files(clone_dir)  # type: ignore[arg-type]
    return build_candidate_pool(pkg_files, header_files)


def _find_extra_packages(
    declared: list[str],
    candidates: list[PackageCandidate],
    repos: list[RepoState],
) -> list[PackageCandidate]:
    """Find candidates matching declared names not yet assigned."""
    existing = {r.package_name for r in repos if r.package_name is not None}
    declared_set = set(declared)
    return [
        c for c in candidates
        if c.stem in declared_set and c.stem not in existing
    ]
