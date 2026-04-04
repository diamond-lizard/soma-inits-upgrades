"""Tests for console module color detection and terminal safety."""

from __future__ import annotations

import soma_inits_upgrades.console as _cmod
from soma_inits_upgrades.console import (
    _reset_terminal_color,
    _should_color,
    eprint_error,
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
