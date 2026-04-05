"""Git diff generation."""

from __future__ import annotations

from subprocess import PIPE
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner

from soma_inits_upgrades.subprocess_utils import SubprocessTimeoutError, resolve_run

GIT_DIFF_TIMEOUT_SECONDS = 120


def generate_diff(
    clone_dir: Path, pinned_ref: str, latest_ref: str,
    output_path: Path,
    run_fn: SubprocessRunner | None = None,
) -> bool:
    """Generate a diff between two refs and write it to output_path.

    Returns True if the diff is non-empty, False if empty.
    Raises RuntimeError on git diff failure or timeout.
    """
    run_fn = resolve_run(run_fn)
    try:
        with output_path.open("wb") as fout:
            result = run_fn(
                ["git", "diff", "--no-color", "--no-ext-diff",
                 pinned_ref, latest_ref, "--"],
                stdout=fout, stderr=PIPE, text=True,
                timeout=GIT_DIFF_TIMEOUT_SECONDS,
                cwd=str(clone_dir),
            )
    except SubprocessTimeoutError as exc:
        output_path.unlink(missing_ok=True)
        msg = (
            f"diff timed out after {GIT_DIFF_TIMEOUT_SECONDS} seconds"
            f" between {pinned_ref} and {latest_ref}"
        )
        raise RuntimeError(msg) from exc
    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        msg = (
            f"git diff failed (exit {result.returncode}):"
            f" {result.stderr.strip()}"
        )
        raise RuntimeError(msg)
    if output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        return False
    return True
