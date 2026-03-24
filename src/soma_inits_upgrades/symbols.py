"""Ripgrep usage search: constants, pattern building, batched search."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import subprocess

    from soma_inits_upgrades.protocols import SubprocessRunner

from soma_inits_upgrades.subprocess_utils import resolve_run

EMACS_DIR: Path = Path.home() / ".emacs.d"

USAGE_SEARCH_EXCLUSION_DIRS: list[Path] = [
    EMACS_DIR / "elpaca",
    EMACS_DIR / "straight",
    EMACS_DIR / "elpa.old",
    EMACS_DIR / "elpaca-upgrade-backup.old",
]

RG_SEARCH_TIMEOUT_SECONDS = 120


def build_elisp_boundary_pattern(symbol: str) -> str:
    """Build a PCRE2 pattern for an elisp symbol with word boundaries.

    Uses negative lookbehind/lookahead with elisp identifier characters
    to prevent false matches on substrings of longer identifiers.
    """
    escaped = re.escape(symbol)
    boundary = r"[a-zA-Z0-9\-_!?/*+=<>]"
    return f"(?<!{boundary}){escaped}(?!{boundary})"


def write_pattern_file(symbols: list[str], tmp_dir: Path) -> Path:
    """Write elisp boundary patterns to a temp file, one per line.

    Returns the path to the written pattern file.
    """
    patterns = [build_elisp_boundary_pattern(s) for s in symbols]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patterns", delete=False, dir=str(tmp_dir),
    ) as fd:
        fd.write("\n".join(patterns) + "\n")
    return Path(fd.name)


def _build_exclude_globs(
    exclude_dirs: list[Path], search_root: Path,
) -> list[str]:
    """Convert exclusion paths to ripgrep --glob arguments."""
    globs: list[str] = []
    for d in exclude_dirs:
        try:
            rel = d.relative_to(search_root)
        except ValueError:
            continue
        globs.extend(["--glob", f"!**/{rel}/**"])
    return globs


def run_batched_rg(
    pattern_file: Path, search_root: Path,
    exclude_dirs: list[Path],
    run_fn: SubprocessRunner | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke ripgrep with patterns from a file and return the result.

    Uses PCRE2 mode, JSON output, and .el file glob filter.
    """
    run_fn = resolve_run(run_fn)
    cmd = [
        "rg", "-P", "-f", str(pattern_file),
        "--json", "--no-ignore", "--glob", "*.el",
        *_build_exclude_globs(exclude_dirs, search_root),
        str(search_root),
    ]
    return run_fn(
        cmd, capture_output=True, text=True,
        timeout=RG_SEARCH_TIMEOUT_SECONDS,
    )
