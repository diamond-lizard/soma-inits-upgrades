"""Tests for subprocess_tracking: poll_with_progress, SIGTERM handler."""

from __future__ import annotations

import pytest
from fake_subprocess import make_fake_popen

from soma_inits_upgrades.subprocess_tracking import poll_with_progress
from soma_inits_upgrades.subprocess_utils import (
    ProcessTracker,
    SubprocessTimeoutError,
    make_sigterm_handler,
)


def test_poll_with_progress_completes(capsys: pytest.CaptureFixture[str]) -> None:
    """poll_with_progress returns stdout/stderr when process completes."""
    fake = make_fake_popen(stdout="out", stderr="err", delay=0.01)
    stdout, stderr = poll_with_progress(
        fake, timeout=5, label="testing", _poll_interval=0.001,
    )
    assert stdout == "out"
    assert stderr == "err"


def test_poll_with_progress_timeout() -> None:
    """poll_with_progress raises SubprocessTimeoutError on timeout."""
    fake = make_fake_popen(delay=999)
    with pytest.raises(SubprocessTimeoutError):
        poll_with_progress(
            fake, timeout=0.01, label="slow", _poll_interval=0.001,
        )
    assert fake.terminated is True


def test_sigterm_handler() -> None:
    """SIGTERM handler terminates tracked process and raises SystemExit."""
    tracker = ProcessTracker()
    fake = make_fake_popen()
    tracker.set(fake)
    handler = make_sigterm_handler(tracker)
    with pytest.raises(SystemExit, match="1"):
        handler(15, None)
    assert fake.terminated is True
