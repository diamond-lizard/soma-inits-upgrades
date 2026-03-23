"""Git operations: clone, default branch detection, rev-parse, safe_rmtree."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner

GIT_CLONE_TIMEOUT_SECONDS = 60


GIT_LOCAL_OP_TIMEOUT_SECONDS = 30


def _default_run(
    args: list[str] | str, **kwargs: object,
) -> subprocess.CompletedProcess[str]:
    """Thin wrapper around subprocess.run matching SubprocessRunner."""
    return subprocess.run(args, **kwargs)  # type: ignore[call-overload, no-any-return]


def _resolve_run(run_fn: SubprocessRunner | None) -> SubprocessRunner:
    """Return run_fn or the default subprocess runner."""
    return run_fn if run_fn is not None else _default_run

def _make_writable_handler(
    func: object, path: str, exc_info: object,
) -> None:
    """onerror handler: make read-only files writable before retrying."""
    os.chmod(path, stat.S_IWRITE)
    if callable(func):
        func(path)


def safe_rmtree(target: Path, containing_dir: Path) -> None:
    """Remove a directory tree, verifying it is inside containing_dir.

    Handles git's read-only pack files via an onerror handler.
    Raises ValueError if target is not inside containing_dir.
    """
    resolved_target = target.resolve()
    resolved_container = containing_dir.resolve()
    if not str(resolved_target).startswith(str(resolved_container) + os.sep):
        msg = f"{resolved_target} is not inside {resolved_container}"
        raise ValueError(msg)
    shutil.rmtree(resolved_target, onerror=_make_writable_handler)


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
    except subprocess.TimeoutExpired:
        return None


def clone_repo(
    repo_url: str, target_dir: Path, containing_dir: Path,
    run_fn: SubprocessRunner | None = None,
) -> tuple[bool, str]:
    """Clone a repository using blobless clone.

    Returns (success, error_message). On timeout, cleans up partial clone.
    """
    run_fn = _resolve_run(run_fn)
    if target_dir.exists():
        safe_rmtree(target_dir, containing_dir)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = run_fn(
            ["git", "clone", "--filter=blob:none", repo_url, str(target_dir)],
            capture_output=True, text=True,
            timeout=GIT_CLONE_TIMEOUT_SECONDS, env=env,
        )
    except subprocess.TimeoutExpired:
        if target_dir.exists():
            safe_rmtree(target_dir, containing_dir)
        return False, "clone timed out after 60 seconds"
    if result.returncode != 0:
        return False, f"clone failed: {result.stderr.strip()}"
    return True, ""


def detect_default_branch(
    clone_dir: Path, run_fn: SubprocessRunner | None = None,
) -> str | None:
    """Determine the default branch via symbolic-ref, fallback main/master."""
    run_fn = _resolve_run(run_fn)
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
    run_fn = _resolve_run(run_fn)
    result = _run_git(
        ["git", "rev-parse", f"origin/{branch}"], clone_dir, run_fn,
    )
    return result.stdout.strip() if result and result.returncode == 0 else None


def verify_ref(
    clone_dir: Path, ref: str,
    run_fn: SubprocessRunner | None = None,
) -> bool:
    """Verify a given ref exists in a cloned repository."""
    run_fn = _resolve_run(run_fn)
    result = _run_git(["git", "cat-file", "-t", ref], clone_dir, run_fn)
    return result is not None and result.returncode == 0


def ensure_working_tree_at_ref(
    clone_dir: Path, ref: str,
    run_fn: SubprocessRunner | None = None,
) -> bool:
    """Ensure the working tree is at the specified commit.

    Returns True on success, False on failure. Does not modify state.
    """
    run_fn = _resolve_run(run_fn)
    result = _run_git(["git", "checkout", ref], clone_dir, run_fn)
    return result is not None and result.returncode == 0
