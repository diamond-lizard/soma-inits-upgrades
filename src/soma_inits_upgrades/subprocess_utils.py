"""Subprocess tracking: SubprocessRunner Protocol, ProcessTracker, tracked_run."""

from __future__ import annotations

import subprocess
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from subprocess import Popen

    from soma_inits_upgrades.protocols import SubprocessRunner


class SubprocessTimeoutError(Exception):
    """Raised when a tracked subprocess exceeds its timeout.

    Includes the command and elapsed time in the message.
    """

    def __init__(self, cmd: list[str] | str, elapsed: float) -> None:
        self.cmd = cmd
        self.elapsed = elapsed
        super().__init__(f"Command {cmd} timed out after {elapsed:.1f}s")


class ProcessTracker:
    """Track the currently active subprocess for SIGTERM cleanup.

    A single instance is created at startup and shared via DI.
    """

    def __init__(self) -> None:
        self._current: Popen[str] | None = None

    @property
    def current(self) -> Popen[str] | None:
        """Return the currently tracked process, or None."""
        return self._current

    def set(self, process: Popen[str]) -> None:
        """Register a subprocess as the active tracked process."""
        self._current = process

    def clear(self) -> None:
        """Unregister the currently tracked process."""
        self._current = None


def terminate_with_escalation(
    process: Popen[str], timeout: float = 5,
) -> None:
    """Terminate a process, escalating to forced stop if needed.

    Calls .terminate(), waits up to timeout seconds, then forces
    process death and waits for exit.
    """
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


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
        print(f"  {label}... ({elapsed:.0f}s)", end="\r", file=sys.stderr)
        time.sleep(_poll_interval)
    stdout, stderr = process.communicate()
    return stdout or "", stderr or ""


def tracked_run(
    args: list[str] | str,
    tracker: ProcessTracker,
    *,
    timeout: float | None = None,
    progress_label: str | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input: str | None = None,  # noqa: A002
    capture_output: bool = False,
    text: bool = False,
    check: bool = False,
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
            stdout, stderr = poll_with_progress(
                process, timeout, progress_label, _poll_interval,
            )
        else:
            try:
                stdout_raw, stderr_raw = process.communicate(input=input, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                elapsed = timeout if timeout is not None else 0.0
                terminate_with_escalation(process)
                raise SubprocessTimeoutError(args, elapsed) from exc
            stdout = stdout_raw or ""
            stderr = stderr_raw or ""
    finally:
        tracker.clear()
    return subprocess.CompletedProcess(
        args, process.returncode or 0, stdout, stderr,
    )



def make_sigterm_handler(
    tracker: ProcessTracker,
) -> Callable[[int, object], None]:
    """Create a SIGTERM handler that cleans up the tracked subprocess.

    Returns a closure suitable for signal.signal(signal.SIGTERM, handler).
    """

    def handler(signum: int, frame: object) -> None:
        if tracker.current is not None:
            terminate_with_escalation(tracker.current)
        raise SystemExit(1)

    return handler
def _default_run(
    args: list[str] | str, **kwargs: object,
) -> subprocess.CompletedProcess[str]:
    """Thin wrapper around subprocess.run matching SubprocessRunner."""
    return subprocess.run(args, **kwargs)  # type: ignore[call-overload, no-any-return]


def resolve_run(run_fn: SubprocessRunner | None) -> SubprocessRunner:
    """Return run_fn or the default subprocess runner."""
    return run_fn if run_fn is not None else _default_run
