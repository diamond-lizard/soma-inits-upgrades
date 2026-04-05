"""Subprocess execution: tracked_run and progress polling."""

from __future__ import annotations

import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from subprocess import Popen

from soma_inits_upgrades.console import eprint
from soma_inits_upgrades.subprocess_utils import (
    ProcessTracker,
    SubprocessTimeoutError,
    terminate_with_escalation,
)


def _communicate_with_timeout(
    process: Popen[str],
    input_data: str | None,
    timeout: float | None,
    args: list[str] | str,
) -> tuple[str, str]:
    """Run process.communicate() with timeout handling.

    Returns (stdout, stderr). Raises SubprocessTimeoutError on timeout.
    """
    try:
        stdout_raw, stderr_raw = process.communicate(
            input=input_data, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = timeout if timeout is not None else 0.0
        terminate_with_escalation(process)
        raise SubprocessTimeoutError(args, elapsed) from exc
    return stdout_raw or "", stderr_raw or ""


def poll_with_progress(
    process: Popen[str], timeout: float | None, label: str,
    _poll_interval: float = 10,
) -> tuple[str, str]:
    """Poll a subprocess, printing elapsed time to stderr.

    Returns (stdout, stderr) when the process exits.
    Raises SubprocessTimeoutError if timeout is exceeded.
    """
    start = time.monotonic()
    while process.poll() is None:
        elapsed = time.monotonic() - start
        if timeout is not None and elapsed >= timeout:
            terminate_with_escalation(process)
            cmd_str = str(process.args) if hasattr(process, "args") else "<unknown>"
            raise SubprocessTimeoutError(cmd_str, elapsed)
        eprint(f"  {label}... ({elapsed:.0f}s)", end="\r")
        time.sleep(_poll_interval)
    stdout, stderr = process.communicate()
    return stdout or "", stderr or ""


def tracked_run(
    args: list[str] | str, tracker: ProcessTracker, *,
    timeout: float | None = None, progress_label: str | None = None,
    cwd: str | None = None, env: dict[str, str] | None = None,
    input: str | None = None, capture_output: bool = False,  # noqa: A002
    text: bool = False, check: bool = False,
    _popen_factory: Callable[..., Popen[str]] | None = None,
    _poll_interval: float = 10,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with process tracking and optional progress.

    Wraps subprocess.Popen, registering/unregistering with the tracker.
    When progress_label is set, polls with elapsed-time output.
    Raises SubprocessTimeoutError on timeout.
    """
    factory = _popen_factory if _popen_factory is not None else subprocess.Popen
    stdin_pipe = subprocess.PIPE if input is not None else None
    process = factory(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=stdin_pipe, text=True, cwd=cwd, env=env,
    )
    tracker.set(process)
    try:
        if progress_label is not None:
            stdout, stderr = poll_with_progress(process, timeout, progress_label, _poll_interval)
        else:
            stdout, stderr = _communicate_with_timeout(process, input, timeout, args)
    finally:
        tracker.clear()
    return subprocess.CompletedProcess(
        args, process.returncode or 0, stdout, stderr,
    )
