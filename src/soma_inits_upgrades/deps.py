"""Package metadata locating and parsing via sexpdata."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_header_parsing import extract_multiline_requires

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.deps_selection import PackageCandidate
    from soma_inits_upgrades.protocols import UserInputFn


def find_pkg_el_files(repo_dir: Path) -> list[Path]:
    """Scan repo root and immediate subdirectories for *-pkg.el files.

    Returns paths sorted with root-level files first, then subdirectory
    files alphabetically.
    """
    root_files = sorted(repo_dir.glob("*-pkg.el"))
    sub_files = sorted(
        f
        for d in sorted(repo_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".")
        for f in d.glob("*-pkg.el")
    )
    return root_files + sub_files

_PKG_REQ_RE = re.compile(r"^;+\s*Package-Requires:")


def find_package_requires_files(repo_dir: Path) -> list[tuple[Path, int]]:
    """Scan .el files in repo root and one level deep for Package-Requires: headers.

    Returns list of (file_path, line_number) tuples, sorted with root-level
    files first, then subdirectory files alphabetically.
    """
    results: list[tuple[Path, int]] = []
    root_els = sorted(repo_dir.glob("*.el"))
    sub_els = sorted(
        f
        for d in sorted(repo_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".")
        for f in d.glob("*.el")
    )
    for path in root_els + sub_els:
        _scan_file_for_header(path, results)
    return results


def _scan_file_for_header(
    path: Path, results: list[tuple[Path, int]],
) -> None:
    """Scan a single .el file for Package-Requires: headers."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    for idx, line in enumerate(lines, start=1):
        if _PKG_REQ_RE.match(line):
            results.append((path, idx))


def locate_package_metadata(
    repo_dir: Path,
    init_file: str | None = None,
    repo_url: str | None = None,
    input_fn: UserInputFn | None = None,
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
