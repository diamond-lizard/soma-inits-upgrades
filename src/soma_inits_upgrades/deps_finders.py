"""File-system scanning for -pkg.el and Package-Requires: header files."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

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
