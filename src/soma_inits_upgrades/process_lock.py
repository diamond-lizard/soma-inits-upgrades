"""Process locking: exclusive flock-based lock for single-instance enforcement."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from io import TextIOWrapper
    from pathlib import Path


def acquire_process_lock(state_dir: Path) -> TextIOWrapper:
    """Acquire an exclusive process lock via flock.

    Opens <state_dir>/lock, acquires LOCK_EX|LOCK_NB, and writes the
    current PID.  On failure, reads the existing PID from the lock file,
    prints an error to stderr, and exits with code 1.  Returns the open
    file object which must be kept alive for the process lifetime.
    """
    import fcntl
    import os

    lock_path = state_dir / "lock"
    fd = open(lock_path, "w")  # noqa: SIM115
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        existing_pid = lock_path.read_text(encoding="utf-8").strip()
        print(
            f"Error: another instance of soma-inits-upgrades is already "
            f"running (PID {existing_pid}). If this is incorrect, delete "
            f"{lock_path} and retry.",
            file=sys.stderr,
        )
        sys.exit(1)
    fd.write(str(os.getpid()))
    fd.flush()
    return fd
