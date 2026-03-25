"""Git ref operations: branch detection, rev-parse, ref verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.subprocess_utils import SubprocessTimeoutError, resolve_run

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner

GIT_LOCAL_OP_TIMEOUT_SECONDS = 30

def _run_git(
    args: list[str], clone_dir: Path, run_fn: SubprocessRunner,
    timeout: int = GIT_LOCAL_OP_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str] | None:
    """Run a git command in clone_dir, returning None on timeout."""
    try:
        return run_fn(
            args, capture_output=True, text=True,
            timeout=timeout, cwd=str(clone_dir),
        )
    except SubprocessTimeoutError:
        return None


def detect_default_branch(
    clone_dir: Path, run_fn: SubprocessRunner | None = None,
) -> str | None:
    """Determine the default branch via symbolic-ref, fallback main/master."""
    run_fn = resolve_run(run_fn)
    result = _run_git(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        clone_dir, run_fn,
    )
    if result and result.returncode == 0:
        return result.stdout.strip().removeprefix("refs/remotes/origin/")
    for name in ("main", "master"):
        check = _run_git(
            ["git", "rev-parse", "--verify", f"refs/remotes/origin/{name}"],
            clone_dir, run_fn,
        )
        if check and check.returncode == 0:
            return name
    return None


def rev_parse(
    clone_dir: Path, branch: str,
    run_fn: SubprocessRunner | None = None,
) -> str | None:
    """Obtain the latest commit SHA on a given branch."""
    run_fn = resolve_run(run_fn)
    result = _run_git(
        ["git", "rev-parse", f"origin/{branch}"], clone_dir, run_fn,
    )
    return result.stdout.strip() if result and result.returncode == 0 else None


def verify_ref(
    clone_dir: Path, ref: str,
    run_fn: SubprocessRunner | None = None,
) -> bool:
    """Verify a given ref exists in a cloned repository."""
    run_fn = resolve_run(run_fn)
    result = _run_git(["git", "cat-file", "-t", ref], clone_dir, run_fn)
    return result is not None and result.returncode == 0


def ensure_working_tree_at_ref(
    clone_dir: Path, ref: str,
    run_fn: SubprocessRunner | None = None,
) -> bool:
    """Ensure the working tree is at the specified commit.

    Returns True on success, False on failure. Does not modify state.
    """
    run_fn = resolve_run(run_fn)
    result = _run_git(["git", "checkout", ref], clone_dir, run_fn)
    return result is not None and result.returncode == 0
