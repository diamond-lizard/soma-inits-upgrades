"""Fake termios and stdin for terminal echo tests."""

from __future__ import annotations

ECHO = 8


class FakeTermios:
    """Fake termios module recording all calls."""

    ECHO = ECHO
    TCIFLUSH = 0
    TCSADRAIN = 1
    error = OSError

    def __init__(self, *, fail_tcgetattr: bool = False) -> None:
        """Initialize with optional failure mode."""
        self.calls: list[tuple[object, ...]] = []
        self._attrs: list[object] = [0, 0, 0, ECHO, 0, 0, []]
        self._fail_tcgetattr = fail_tcgetattr

    def tcgetattr(self, fd: int) -> list[object]:
        """Record call and return current attrs."""
        if self._fail_tcgetattr:
            raise self.error("not a terminal")
        self.calls.append(("tcgetattr", fd))
        return list(self._attrs)

    def tcsetattr(
        self, fd: int, when: int, attrs: list[object],
    ) -> None:
        """Record call and update stored attrs."""
        self.calls.append(("tcsetattr", fd, when, list(attrs)))
        self._attrs = list(attrs)

    def tcflush(self, fd: int, queue: int) -> None:
        """Record call."""
        self.calls.append(("tcflush", fd, queue))


class FakeStdin:
    """Fake stdin with configurable isatty()."""

    def __init__(self, *, is_tty: bool = True) -> None:
        """Initialize with TTY flag."""
        self._is_tty = is_tty

    def isatty(self) -> bool:
        """Return configured TTY status."""
        return self._is_tty

    def fileno(self) -> int:
        """Return fake file descriptor."""
        return 0
