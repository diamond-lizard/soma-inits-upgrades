"""Tests for terminal echo state management."""

from __future__ import annotations

import pytest
from fake_termios import ECHO, FakeStdin, FakeTermios

from soma_inits_upgrades.terminal import TerminalEcho


def test_noop_when_not_tty() -> None:
    """suppressed() and for_input() are no-ops when not a TTY."""
    fake = FakeTermios()
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin(is_tty=False))
    with te.suppressed(), te.for_input():
        pass
    assert fake.calls == []


def test_for_input_passthrough_outside_suppressed() -> None:
    """for_input() is a no-op when called outside suppressed()."""
    fake = FakeTermios()
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin())
    with te.for_input():
        pass
    assert fake.calls == []


def test_nested_suppressed_is_noop() -> None:
    """Nested suppressed() does not modify terminal state."""
    fake = FakeTermios()
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin())
    with te.suppressed():
        calls_before = len(fake.calls)
        with te.suppressed():
            pass
        assert len(fake.calls) == calls_before
    assert te._active is False


def test_suppressed_saves_disables_restores() -> None:
    """suppressed() saves attrs, disables ECHO, restores on exit."""
    fake = FakeTermios()
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin())
    with te.suppressed():
        sets = [c for c in fake.calls if c[0] == "tcsetattr"]
        assert sets[-1][3][3] & ECHO == 0
    sets = [c for c in fake.calls if c[0] == "tcsetattr"]
    assert sets[-1][3][3] & ECHO == ECHO


def test_for_input_flushes_and_restores() -> None:
    """for_input() flushes stdin, restores echo, re-suppresses."""
    fake = FakeTermios()
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin())
    with te.suppressed():
        fake.calls.clear()
        with te.for_input():
            flush = [c for c in fake.calls if c[0] == "tcflush"]
            assert len(flush) == 1
            sets = [c for c in fake.calls if c[0] == "tcsetattr"]
            assert sets[0][3][3] & ECHO == ECHO
        sets = [c for c in fake.calls if c[0] == "tcsetattr"]
        assert sets[-1][3][3] & ECHO == 0


def test_suppressed_restores_on_exception() -> None:
    """Terminal state is restored even when an exception occurs."""
    fake = FakeTermios()
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin())
    with pytest.raises(RuntimeError), te.suppressed():
        raise RuntimeError("boom")
    sets = [c for c in fake.calls if c[0] == "tcsetattr"]
    assert sets[-1][3][3] & ECHO == ECHO
    assert te._active is False


def test_tcgetattr_error_falls_back_to_noop() -> None:
    """suppressed() is a no-op when tcgetattr raises error."""
    fake = FakeTermios(fail_tcgetattr=True)
    te = TerminalEcho(_termios=fake, _stdin=FakeStdin())
    with te.suppressed():
        pass
    assert te._active is False
