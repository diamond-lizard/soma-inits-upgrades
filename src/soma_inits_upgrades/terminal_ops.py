"""Low-level termios operations for terminal echo management."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any


def save_and_suppress(
    termios_mod: ModuleType, stdin: Any,
) -> list[Any] | None:
    """Save terminal attrs and disable ECHO flag.

    Returns saved attributes, or None if the operation fails.
    """
    try:
        fd = stdin.fileno()
        saved: list[Any] = termios_mod.tcgetattr(fd)
        new = list(saved)
        new[3] &= ~termios_mod.ECHO
        termios_mod.tcsetattr(fd, termios_mod.TCSADRAIN, new)
    except termios_mod.error:
        return None
    return saved


def restore_attrs(
    termios_mod: ModuleType,
    stdin: Any,
    saved: list[Any] | None,
) -> None:
    """Restore previously saved terminal attributes."""
    if saved is None:
        return
    with suppress(termios_mod.error):
        termios_mod.tcsetattr(
            stdin.fileno(), termios_mod.TCSADRAIN, saved,
        )


def flush_and_restore(
    termios_mod: ModuleType,
    stdin: Any,
    saved: list[Any] | None,
) -> None:
    """Flush stdin buffer and restore saved terminal attrs."""
    if saved is None:
        return
    with suppress(termios_mod.error):
        fd = stdin.fileno()
        termios_mod.tcflush(fd, termios_mod.TCIFLUSH)
        termios_mod.tcsetattr(
            fd, termios_mod.TCSADRAIN, saved,
        )


def suppress_echo(termios_mod: ModuleType, stdin: Any) -> None:
    """Read current terminal attrs and suppress ECHO flag."""
    with suppress(termios_mod.error):
        fd = stdin.fileno()
        attrs = termios_mod.tcgetattr(fd)
        attrs[3] &= ~termios_mod.ECHO
        termios_mod.tcsetattr(fd, termios_mod.TCSADRAIN, attrs)
