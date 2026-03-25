"""Fake subprocess classes for testing subprocess tracking."""

from __future__ import annotations

import subprocess
import time


class FakePopen:
    """Fake subprocess.Popen for testing tracked_run."""

    def __init__(
        self, *, exit_code: int = 0,
        stdout: str = "", stderr: str = "",
        delay: float | None = None,
    ) -> None:
        self.returncode: int | None = None
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        self._delay = delay
        self.terminated = False
        self.killed = False
        self.pid = 12345
        self.args: list[str] = ["fake"]
        self._started = time.monotonic()

    def communicate(
        self, input: str | None = None,  # noqa: A002
        timeout: float | None = None,
    ) -> tuple[str, str]:
        """Return stdout/stderr, raising TimeoutExpired if needed."""
        if self._delay is not None and timeout is not None and timeout < self._delay:
            raise subprocess.TimeoutExpired("fake", timeout)
        if self._delay is not None:
            time.sleep(self._delay)
        self.returncode = self._exit_code
        return self._stdout, self._stderr

    def poll(self) -> int | None:
        """Return exit code if process has finished."""
        if self._delay is None:
            self.returncode = self._exit_code
            return self._exit_code
        elapsed = time.monotonic() - self._started
        if elapsed >= self._delay:
            self.returncode = self._exit_code
            return self._exit_code
        return None

    def terminate(self) -> None:
        """Record that terminate was called."""
        self.terminated = True
        self.returncode = self._exit_code

    def kill(self) -> None:
        """Record that forced stop was called."""
        self.killed = True
        self.returncode = self._exit_code

    def wait(self, timeout: float | None = None) -> int:
        """Return exit code."""
        self.returncode = self._exit_code
        return self._exit_code


def make_fake_popen(
    *, exit_code: int = 0,
    stdout: str = "", stderr: str = "",
    delay: float | None = None,
) -> FakePopen:
    """Create a FakePopen instance with configurable behavior."""
    return FakePopen(
        exit_code=exit_code, stdout=stdout,
        stderr=stderr, delay=delay,
    )
