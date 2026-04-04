"""Tests for console module stderr output functions."""

from __future__ import annotations

from soma_inits_upgrades.console import (
    eprint,
    eprint_error,
    eprint_plain,
    eprint_prompt,
    eprint_warn,
    stderr_console,
)


def test_eprint_writes_to_stderr(capfd: object) -> None:
    """eprint() output appears on stderr, not stdout."""
    eprint("hello from eprint")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "hello from eprint" in captured.err
    assert captured.out == ""


def test_stderr_console_targets_stderr() -> None:
    """stderr_console is configured to write to stderr."""
    assert stderr_console.stderr is True


def test_eprint_error_writes_to_stderr(capfd: object) -> None:
    """eprint_error() output appears on stderr."""
    eprint_error("something went wrong")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "something went wrong" in captured.err


def test_eprint_warn_writes_to_stderr(capfd: object) -> None:
    """eprint_warn() output appears on stderr."""
    eprint_warn("watch out")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "watch out" in captured.err


def test_eprint_prompt_writes_to_stderr(capfd: object) -> None:
    """eprint_prompt() output appears on stderr."""
    eprint_prompt("choose an option")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "choose an option" in captured.err


def test_eprint_plain_writes_to_stderr(capfd: object) -> None:
    """eprint_plain() output appears on stderr."""
    eprint_plain("plain message")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "plain message" in captured.err


def test_eprint_end_parameter(capfd: object) -> None:
    """The end parameter controls line endings."""
    eprint("hello", end="")
    eprint(" world")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert captured.err == "hello world\n"
