"""Extract (use-package ...) declarations from Emacs init files."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_COMMENT_RE = re.compile(r"^\s*;")
_USE_PKG_RE = re.compile(r"^\s*\(use-package\s+(\S+)")


def extract_use_package_names(init_file_path: Path) -> list[str]:
    """Return package names from (use-package ...) declarations in an init file.

    Scans each line for declarations like ``(use-package dash`` while
    ignoring commented-out lines (any line whose first non-whitespace
    character is a semicolon).  Returns names in the order they appear.
    Returns an empty list if the file is missing, unreadable, or has no
    declarations.
    """
    try:
        lines = init_file_path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return []
    names: list[str] = []
    for line in lines:
        if _COMMENT_RE.search(line):
            continue
        m = _USE_PKG_RE.match(line)
        if m:
            names.append(m.group(1))
    return names
