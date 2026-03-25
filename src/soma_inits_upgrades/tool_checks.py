"""Startup tool validation: git availability, git version, rg availability, rg PCRE2."""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import SubprocessRunner, WhichFn

MIN_GIT_VERSION = (2, 19)


def check_git_available(which_fn: WhichFn) -> str:
    """Verify git is on PATH. Returns the path, or exits with code 1."""
    path = which_fn("git")
    if path is None:
        print("Error: git is not installed or not on PATH.", file=sys.stderr)
        raise SystemExit(1)
    return path


def check_git_version(
    git_path: str, run_fn: SubprocessRunner,
) -> None:
    """Verify git >= 2.19. Exits with code 1 if below."""
    result = run_fn([git_path, "--version"], capture_output=True, text=True)
    match = re.search(r"(\d+)\.(\d+)", result.stdout)
    if match is None:
        print(f"Error: could not parse git version from: {result.stdout.strip()}", file=sys.stderr)
        raise SystemExit(1)
    major, minor = int(match.group(1)), int(match.group(2))
    if (major, minor) < MIN_GIT_VERSION:
        version_str = f"{major}.{minor}"
        msg = (
            f"Error: git 2.19+ is required for partial (blobless) clones."
            f" Found version {version_str}."
        )
        print(msg, file=sys.stderr)
        raise SystemExit(1)


def check_rg_available(which_fn: WhichFn) -> str:
    """Verify rg is on PATH. Returns the path, or exits with code 1."""
    path = which_fn("rg")
    if path is None:
        print("Error: rg (ripgrep) is not installed or not on PATH.", file=sys.stderr)
        raise SystemExit(1)
    return path


def check_rg_pcre2(
    rg_path: str, run_fn: SubprocessRunner,
) -> None:
    """Verify rg has PCRE2 support. Exits with code 1 if not."""
    result = run_fn(
        [rg_path, "-P", "test"],
        capture_output=True, text=True, input="test",
    )
    if result.returncode != 0:
        msg = (
            "Error: ripgrep does not have PCRE2 support, which is required"
            " for elisp symbol search. Install ripgrep with PCRE2"
            " (e.g., cargo install ripgrep)."
        )
        print(msg, file=sys.stderr)
        raise SystemExit(1)
