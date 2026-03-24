"""Package metadata locating and parsing via sexpdata."""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_header_parsing import extract_multiline_requires
from soma_inits_upgrades.deps_parsing import parse_pkg_el

if TYPE_CHECKING:
    from pathlib import Path


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
) -> tuple[str | None, str | None]:
    """Locate and parse package dependency metadata from a repository.

    Prefers -pkg.el files over Package-Requires: headers.  Prefers
    root-level files over subdirectory files.  Returns
    (raw_deps_sexp, package_name) or (None, None) if no metadata found.
    """
    pkg_files = find_pkg_el_files(repo_dir)
    header_files = find_package_requires_files(repo_dir)
    if pkg_files:
        return parse_pkg_el(pkg_files[0])
    if header_files:
        return _metadata_from_header(header_files)
    return None, None


def _metadata_from_header(
    header_files: list[tuple[Path, int]],
) -> tuple[str | None, str | None]:
    """Extract metadata from the first Package-Requires: header file."""
    path, line_num = header_files[0]
    if len(header_files) > 1:
        names = ", ".join(str(h[0].name) for h in header_files[1:])
        print(
            f"Warning: ignoring Package-Requires in: {names}",
            file=sys.stderr,
        )
    lines = path.read_text(encoding="utf-8").splitlines()
    raw = extract_multiline_requires(lines, line_num - 1)
    pkg_name = path.stem
    return raw, pkg_name
