"""Tests for subprocess_utils: tracked_run, ProcessTracker, SIGTERM handler."""

from __future__ import annotations

import subprocess

import pytest
from conftest import FakePopen, make_fake_popen

from soma_inits_upgrades.subprocess_utils import (
    ProcessTracker,
    SubprocessTimeoutError,
    make_sigterm_handler,
    terminate_with_escalation,
    tracked_run,
)


def test_tracked_run_happy_path() -> None:
    """tracked_run returns CompletedProcess with correct fields."""
    tracker = ProcessTracker()
    fake = make_fake_popen(exit_code=0, stdout="ok\n", stderr="")
    result = tracked_run(
        ["echo"], tracker, _popen_factory=lambda *a, **kw: fake,
    )
    assert result.returncode == 0
    assert result.stdout == "ok\n"
    assert tracker.current is None


def test_terminate_with_escalation_basic() -> None:
    """terminate_with_escalation calls .terminate()."""
    fake = make_fake_popen()
    terminate_with_escalation(fake)
    assert fake.terminated is True


def test_terminate_with_escalation_escalates() -> None:
    """Escalates to .kill() when .wait() raises TimeoutExpired."""

    class StubPopen(FakePopen):
        """FakePopen whose .wait() always times out first call."""

        def __init__(self) -> None:
            super().__init__()
            self._wait_count = 0

        def wait(self, timeout: float | None = None) -> int:
            """Raise TimeoutExpired on first call."""
            self._wait_count += 1
            if self._wait_count == 1:
                raise subprocess.TimeoutExpired("fake", timeout or 0)
            self.returncode = 0
            return 0

    fake = StubPopen()
    terminate_with_escalation(fake, timeout=0.01)
    assert fake.terminated is True
    assert fake.killed is True


def test_tracked_run_timeout() -> None:
    """tracked_run raises SubprocessTimeoutError on timeout."""
    tracker = ProcessTracker()
    fake = make_fake_popen(delay=10)
    with pytest.raises(SubprocessTimeoutError):
        tracked_run(
            ["slow"], tracker, timeout=0.01,
            _popen_factory=lambda *a, **kw: fake,
        )
    assert fake.terminated is True
    assert tracker.current is None


def test_tracker_lifecycle() -> None:
    """ProcessTracker.current is set during communicate, cleared after."""
    tracker = ProcessTracker()
    seen_during: list[bool] = []

    class SpyPopen(FakePopen):
        """FakePopen that records tracker state during communicate."""

        def communicate(
            self, input: str | None = None,  # noqa: A002
            timeout: float | None = None,
        ) -> tuple[str, str]:
            """Record whether tracker.current is set."""
            seen_during.append(tracker.current is not None)
            return super().communicate(timeout=timeout)

    fake = SpyPopen()
    tracked_run(["test"], tracker, _popen_factory=lambda *a, **kw: fake)
    assert seen_during == [True]
    assert tracker.current is None


def test_sigterm_handler() -> None:
    """SIGTERM handler terminates tracked process and raises SystemExit."""
    tracker = ProcessTracker()
    fake = make_fake_popen()
    tracker.set(fake)
    handler = make_sigterm_handler(tracker)
    with pytest.raises(SystemExit, match="1"):
        handler(15, None)
    assert fake.terminated is True


def test_poll_with_progress_completes(capsys: pytest.CaptureFixture[str]) -> None:
    """poll_with_progress returns stdout/stderr when process completes."""
    from soma_inits_upgrades.subprocess_utils import poll_with_progress

    fake = make_fake_popen(stdout="out", stderr="err", delay=0.01)
    stdout, stderr = poll_with_progress(fake, timeout=5, label="testing", _poll_interval=0.001)
    assert stdout == "out"
    assert stderr == "err"


def test_poll_with_progress_timeout() -> None:
    """poll_with_progress raises SubprocessTimeoutError on timeout."""
    from soma_inits_upgrades.subprocess_utils import poll_with_progress

    fake = make_fake_popen(delay=999)
    with pytest.raises(SubprocessTimeoutError):
        poll_with_progress(fake, timeout=0.01, label="slow", _poll_interval=0.001)
    assert fake.terminated is True
