"""Package metadata locating and parsing via sexpdata."""

from __future__ import annotations

import re
import sys
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


def parse_pkg_el(path: Path) -> tuple[str | None, str | None]:
    """Parse a -pkg.el file and return (raw_deps_sexp, package_name).

    The file contains (define-package NAME VERSION [DOCSTRING] REQUIREMENTS).
    DOCSTRING is optional; REQUIREMENTS may be quote-prefixed.
    Returns (None, None) if the file cannot be parsed or has too few arguments.
    """
    import sexpdata

    try:
        text = path.read_text(encoding="utf-8")
        parsed = sexpdata.loads(text)
    except (OSError, UnicodeDecodeError, ValueError):
        return None, None
    if not isinstance(parsed, list) or len(parsed) < 3:
        return None, None
    pkg_name = _extract_string(parsed[1])
    reqs_arg = _select_requirements_arg(parsed)
    if reqs_arg is None:
        return None, pkg_name
    raw = _unwrap_to_string(reqs_arg)
    return raw, pkg_name


def _extract_string(val: object) -> str | None:
    """Extract a plain string from a sexpdata value."""
    import sexpdata

    if isinstance(val, str):
        return val
    if isinstance(val, sexpdata.Symbol):
        return val.value()
    return None


def _select_requirements_arg(parsed: list[object]) -> object | None:
    """Pick the REQUIREMENTS argument from a define-package form.

    If the 3rd arg is a string it is the DOCSTRING; REQUIREMENTS is the 4th.
    If the 3rd arg is a list or Quoted, it is REQUIREMENTS directly.
    """
    import sexpdata

    third = parsed[2]
    if isinstance(third, str):
        return parsed[3] if len(parsed) > 3 else None
    if isinstance(third, (list, sexpdata.Quoted)):
        return third
    return None


def _unwrap_to_string(val: object) -> str:
    """Convert a sexpdata value to its string representation.

    Unwraps Quoted wrappers and converts lists to s-expression strings.
    """
    import sexpdata

    if isinstance(val, sexpdata.Quoted):
        val = val.x
    if isinstance(val, list):
        return sexpdata.dumps(val)
    if isinstance(val, str):
        return val
    return str(val)


_CONTINUATION_RE = re.compile(r"^;+\s+")


def extract_multiline_requires(lines: list[str], header_line_idx: int) -> str:
    """Extract a Package-Requires: value that may span continuation lines.

    Starts after the colon on the header line, then accumulates subsequent
    lines starting with semicolons followed by whitespace.  Stops when
    parentheses are balanced.
    """
    header = lines[header_line_idx]
    value = header.split("Package-Requires:", 1)[1].strip()
    for line in lines[header_line_idx + 1 :]:
        if _is_balanced(value):
            break
        m = _CONTINUATION_RE.match(line)
        if not m:
            break
        value += " " + line[m.end() :]
    return value.strip()


def _is_balanced(text: str) -> bool:
    """Return True when opening and closing parens are equal and non-zero."""
    opens = text.count("(")
    return opens > 0 and opens == text.count(")")


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
