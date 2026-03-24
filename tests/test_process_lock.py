"""Tests for process_lock.py (acquire_process_lock)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.process_lock import acquire_process_lock

if TYPE_CHECKING:
    from pathlib import Path


def test_lock_creates_file_and_writes_pid(tmp_path: Path) -> None:
    """Acquiring lock creates lock file with current PID."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    fd = acquire_process_lock(state_dir)
    lock_path = state_dir / "lock"
    assert lock_path.is_file()
    content = lock_path.read_text().strip()
    assert content == str(os.getpid())
    fd.close()


_LOCK_HOLDER_SCRIPT = """\
import sys, time, fcntl
state_dir = sys.argv[1]
lock_path = state_dir + "/lock"
fd = open(lock_path, "w")
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
fd.write(str(__import__("os").getpid()))
fd.flush()
print("LOCKED", flush=True)
time.sleep(30)
"""


@pytest.mark.timeout(10)
def test_lock_rejects_second_instance(tmp_path: Path) -> None:
    """Second acquisition fails with error mentioning holder PID."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    proc = subprocess.Popen(
        [sys.executable, "-c", _LOCK_HOLDER_SCRIPT, str(state_dir)],
        stdout=subprocess.PIPE, text=True,
    )
    assert proc.stdout is not None
    proc.stdout.readline()  # wait for "LOCKED"
    with pytest.raises(SystemExit) as exc_info:
        acquire_process_lock(state_dir)
    assert exc_info.value.code == 1
    proc.terminate()
    proc.wait()


@pytest.mark.timeout(10)
def test_lock_released_on_process_exit(tmp_path: Path) -> None:
    """Lock can be reacquired after holder exits."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    proc = subprocess.Popen(
        [sys.executable, "-c", _LOCK_HOLDER_SCRIPT, str(state_dir)],
        stdout=subprocess.PIPE, text=True,
    )
    assert proc.stdout is not None
    proc.stdout.readline()  # wait for "LOCKED"
    proc.terminate()
    proc.wait()
    time.sleep(0.1)
    fd = acquire_process_lock(state_dir)
    assert (state_dir / "lock").read_text().strip() == str(os.getpid())
    fd.close()
