"""Git operations: clone, default branch detection, rev-parse, safe_rmtree."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


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
