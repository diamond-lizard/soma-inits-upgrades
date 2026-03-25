"""Subprocess tracking: SubprocessTimeoutError, ProcessTracker, SIGTERM handler."""

from __future__ import annotations

import subprocess
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


def make_sigterm_handler(
    tracker: ProcessTracker,
) -> Callable[[int, object], None]:
    """Create a SIGTERM handler that cleans up the tracked subprocess.

    Returns a closure suitable for signal.signal(signal.SIGTERM, handler).
    """

    def handler(signum: int, frame: object) -> None:
        """Terminate tracked process and exit."""
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
