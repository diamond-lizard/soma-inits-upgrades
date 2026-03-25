"""Git operations: clone, safe_rmtree."""

from __future__ import annotations

import os
import shutil
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner

from soma_inits_upgrades.subprocess_utils import SubprocessTimeoutError, resolve_run

GIT_CLONE_TIMEOUT_SECONDS = 60


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


def clone_repo(
    repo_url: str, target_dir: Path, containing_dir: Path,
    run_fn: SubprocessRunner | None = None,
) -> tuple[bool, str]:
    """Clone a repository using blobless clone.

    Returns (success, error_message). On timeout, cleans up partial clone.
    """
    run_fn = resolve_run(run_fn)
    if target_dir.exists():
        safe_rmtree(target_dir, containing_dir)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = run_fn(
            ["git", "clone", "--filter=blob:none", repo_url, str(target_dir)],
            capture_output=True, text=True,
            timeout=GIT_CLONE_TIMEOUT_SECONDS, env=env,
        )
    except SubprocessTimeoutError:
        if target_dir.exists():
            safe_rmtree(target_dir, containing_dir)
        return False, "clone timed out after 60 seconds"
    if result.returncode != 0:
        return False, f"clone failed: {result.stderr.strip()}"
    return True, ""

