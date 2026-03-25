"""Tests for subprocess_utils: tracked_run, ProcessTracker, escalation."""

from __future__ import annotations

import subprocess

import pytest
from fake_subprocess import FakePopen, make_fake_popen

from soma_inits_upgrades.subprocess_tracking import tracked_run
from soma_inits_upgrades.subprocess_utils import (
    ProcessTracker,
    SubprocessTimeoutError,
    terminate_with_escalation,
)


class StubTimeoutPopen(FakePopen):
    """FakePopen whose .wait() raises TimeoutExpired on first call."""

    def __init__(self) -> None:
        super().__init__()
        self._wait_count = 0

    def wait(self, timeout: float | None = None) -> int:
        """Raise TimeoutExpired on first call, succeed on second."""
        self._wait_count += 1
        if self._wait_count == 1:
            raise subprocess.TimeoutExpired("fake", timeout or 0)
        self.returncode = 0
        return 0


class SpyTrackerPopen(FakePopen):
    """FakePopen that records tracker state during communicate."""

    def __init__(self, tracker: ProcessTracker) -> None:
        super().__init__()
        self._tracker = tracker
        self.seen_during: list[bool] = []

    def communicate(
        self, input: str | None = None,  # noqa: A002
        timeout: float | None = None,
    ) -> tuple[str, str]:
        """Record whether tracker.current is set."""
        self.seen_during.append(self._tracker.current is not None)
        return super().communicate(timeout=timeout)


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
    """Escalates to forced stop when .wait() raises TimeoutExpired."""
    fake = StubTimeoutPopen()
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
    fake = SpyTrackerPopen(tracker)
    tracked_run(["test"], tracker, _popen_factory=lambda *a, **kw: fake)
    assert fake.seen_during == [True]
    assert tracker.current is None
