"""Tests for console module colored stderr output functions."""

from __future__ import annotations

import soma_inits_upgrades.console as _cmod
from soma_inits_upgrades.console import (
    _reset_terminal_color,
    _should_color,
    eprint,
    eprint_error,
    eprint_plain,
    eprint_prompt,
    eprint_warn,
    stderr_console,
)


class _FakeStream:
    """Minimal stream fake with configurable isatty."""

    def __init__(self, *, tty: bool) -> None:
        self.written: list[str] = []
        self.flushed: list[bool] = []
        self._tty = tty

    def write(self, s: str) -> None:
        self.written.append(s)

    def flush(self) -> None:
        self.flushed.append(True)

    def isatty(self) -> bool:
        return self._tty


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


def test_should_color_false_when_no_color_set(monkeypatch: object) -> None:
    """_should_color() returns False when NO_COLOR is set."""
    monkeypatch.setenv("NO_COLOR", "1")  # type: ignore[attr-defined]
    monkeypatch.delenv("FORCE_COLOR", raising=False)  # type: ignore[attr-defined]
    assert _should_color() is False


def test_should_color_true_when_force_color_set(monkeypatch: object) -> None:
    """_should_color() returns True when FORCE_COLOR is set."""
    monkeypatch.setenv("FORCE_COLOR", "1")  # type: ignore[attr-defined]
    monkeypatch.delenv("NO_COLOR", raising=False)  # type: ignore[attr-defined]
    assert _should_color() is True


def test_no_color_takes_precedence_over_force_color(monkeypatch: object) -> None:
    """NO_COLOR takes precedence over FORCE_COLOR."""
    monkeypatch.setenv("NO_COLOR", "1")  # type: ignore[attr-defined]
    monkeypatch.setenv("FORCE_COLOR", "1")  # type: ignore[attr-defined]
    assert _should_color() is False


def test_eprint_error_emits_ansi_when_force_color(capfd: object, monkeypatch: object) -> None:
    """eprint_error() produces ANSI codes when FORCE_COLOR is set."""
    monkeypatch.setenv("FORCE_COLOR", "1")  # type: ignore[attr-defined]
    monkeypatch.delenv("NO_COLOR", raising=False)  # type: ignore[attr-defined]
    eprint_error("red text")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert "\033[31m" in captured.err


def test_eprint_end_parameter(capfd: object) -> None:
    """The end parameter controls line endings."""
    eprint("hello", end="")
    eprint(" world")
    captured = capfd.readouterr()  # type: ignore[attr-defined]
    assert captured.err == "hello world\n"


def test_reset_terminal_color_writes_when_tty() -> None:
    """_reset_terminal_color writes reset when color was emitted."""
    stream = _FakeStream(tty=True)
    _cmod._color_emitted = True
    try:
        _reset_terminal_color(_stderr=stream)
    finally:
        _cmod._color_emitted = False
    assert stream.written == ["\033[0m"]
    assert stream.flushed == [True]


def test_reset_terminal_color_skips_when_not_tty() -> None:
    """_reset_terminal_color skips reset when stream is not a tty."""
    stream = _FakeStream(tty=False)
    _cmod._color_emitted = True
    try:
        _reset_terminal_color(_stderr=stream)
    finally:
        _cmod._color_emitted = False
    assert stream.written == []
