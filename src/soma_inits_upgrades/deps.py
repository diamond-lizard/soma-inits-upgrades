"""Package metadata locating and parsing via sexpdata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_finders import (
    find_package_requires_files,
    find_pkg_el_files,
)
from soma_inits_upgrades.deps_header_parsing import extract_multiline_requires

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.deps_selection import PackageCandidate
    from soma_inits_upgrades.protocols import UserInputFn


def locate_package_metadata(
    repo_dir: Path,
    init_file: str | None = None,
    repo_url: str | None = None,
    input_fn: UserInputFn | None = None,
    inits_dir: Path | None = None,
) -> tuple[str | None, str | None]:
    """Locate and parse package dependency metadata from a repository.

    Merges -pkg.el and header candidates into a deduplicated pool.
    Prompts the user to select when multiple candidates exist.
    Returns (raw_deps_sexp, package_name) or (None, None).
    """
    from soma_inits_upgrades.deps_candidate_pool import build_candidate_pool
    from soma_inits_upgrades.deps_selection import select_package_file

    pkg_files = find_pkg_el_files(repo_dir)
    header_files = find_package_requires_files(repo_dir)
    candidates = build_candidate_pool(pkg_files, header_files)
    candidates = _filter_by_use_package(candidates, init_file, inits_dir)
    if not candidates:
        return None, None
    if len(candidates) == 1:
        selected = candidates[0]
    else:
        selected = select_package_file(
            candidates, init_file, repo_url, input_fn,
        )
    return _parse_selected(selected)


def _parse_selected(
    selected: PackageCandidate,
) -> tuple[str | None, str | None]:
    """Dispatch parsing based on the selected candidate's source type."""
    if selected.source_type == "pkg_el":
        return selected.raw_deps, selected.embedded_name or selected.stem
    lines = selected.path.read_text(encoding="utf-8").splitlines()
    assert selected.header_line is not None
    raw = extract_multiline_requires(lines, selected.header_line - 1)
    return raw, selected.stem

def _filter_by_use_package(
    candidates: list[PackageCandidate],
    init_file: str | None,
    inits_dir: Path | None,
) -> list[PackageCandidate]:
    """Narrow candidates to those matching use-package declarations.

    Returns the filtered list if any candidates match, otherwise
    returns the original list unchanged (fallback).
    """
    if inits_dir is None or init_file is None:
        return candidates
    from soma_inits_upgrades.use_package_parser import extract_use_package_names

    declared = extract_use_package_names(inits_dir / init_file)
    if not declared:
        return candidates
    filtered = [c for c in candidates if c.stem in declared]
    return filtered if filtered else candidates
