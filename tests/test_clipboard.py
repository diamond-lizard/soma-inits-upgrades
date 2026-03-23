#!/usr/bin/env python3
"""Tests for clipboard.py (xclip detection and copy)."""

from __future__ import annotations

import subprocess

from soma_inits_upgrades.clipboard import copy_to_primary, make_xclip_checker


def test_xclip_checker_available() -> None:
    """Checker returns True when which_fn finds xclip."""
    checker = make_xclip_checker(which_fn=lambda name: "/usr/bin/xclip")
    assert checker() is True


def test_xclip_checker_not_available() -> None:
    """Checker returns False when which_fn returns None."""
    checker = make_xclip_checker(which_fn=lambda name: None)
    assert checker() is False


def test_xclip_checker_caches_result() -> None:
    """Checker calls which_fn only once and caches the result."""
    call_count = 0

    def counting_which(name: str) -> str | None:
        nonlocal call_count
        call_count += 1
        return "/usr/bin/xclip"

    checker = make_xclip_checker(which_fn=counting_which)
    checker()
    checker()
    checker()
    assert call_count == 1


def test_xclip_checker_separate_instances_isolated() -> None:
    """Different checker instances have independent caches."""
    checker_yes = make_xclip_checker(which_fn=lambda name: "/usr/bin/xclip")
    checker_no = make_xclip_checker(which_fn=lambda name: None)
    assert checker_yes() is True
    assert checker_no() is False


def test_copy_to_primary_calls_xclip() -> None:
    """copy_to_primary calls run_fn with correct xclip arguments."""
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(
        args: list[str], **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)

    copy_to_primary("hello world", run_fn=fake_run)
    assert len(calls) == 1
    assert calls[0][0] == ["xclip", "-selection", "primary"]
    assert calls[0][1]["input"] == "hello world"
    assert calls[0][1]["text"] is True
    assert calls[0][1]["check"] is True


def test_copy_to_primary_handles_failure() -> None:
    """copy_to_primary prints warning on xclip failure, does not raise."""
    def failing_run(
        args: list[str], **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, "xclip")

    copy_to_primary("text", run_fn=failing_run)


def test_copy_to_primary_handles_timeout() -> None:
    """copy_to_primary handles TimeoutExpired gracefully."""
    def timeout_run(
        args: list[str], **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("xclip", 5)

    copy_to_primary("text", run_fn=timeout_run)


def test_copy_to_primary_handles_oserror() -> None:
    """copy_to_primary handles OSError gracefully."""
    def oserror_run(
        args: list[str], **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("xclip not found")

    copy_to_primary("text", run_fn=oserror_run)
