"""Tests for rich console foundation module."""

from __future__ import annotations

from soma_inits_upgrades.console import eprint, stderr_console


def test_eprint_writes_to_stderr(capfd: object) -> None:
    """eprint() output appears on stderr, not stdout."""
    eprint("hello from eprint")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "hello from eprint" in captured.err
    assert captured.out == ""


def test_stderr_console_targets_stderr() -> None:
    """stderr_console is configured to write to stderr."""
    assert stderr_console.stderr is True
