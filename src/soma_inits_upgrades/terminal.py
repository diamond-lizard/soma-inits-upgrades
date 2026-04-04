"""Terminal echo state management for non-interactive phases."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING

from soma_inits_upgrades.terminal_ops import (
    flush_and_restore,
    restore_attrs,
    save_and_suppress,
    suppress_echo,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType
    from typing import Any


class TerminalEcho:
    """Manages terminal ECHO flag during non-interactive phases.

    Context managers: suppressed() disables echo for non-interactive
    phases; for_input() temporarily restores echo for prompts.
    All operations are no-ops when stdin is not a TTY.
    """

    def __init__(
        self,
        *,
        _termios: ModuleType | None = None,
        _stdin: Any = None,
    ) -> None:
        """Initialize with optional test doubles for DI."""
        if _termios is None:
            import termios
            _termios = termios
        self._termios = _termios
        self._stdin = _stdin if _stdin is not None else sys.stdin
        self._active = False
        self._saved_attrs: list[Any] | None = None

    @contextmanager
    def suppressed(self) -> Iterator[None]:
        """Suppress terminal echo for non-interactive phases."""
        if self._active or not self._stdin.isatty():
            yield
            return
        self._active = True
        self._saved_attrs = save_and_suppress(
            self._termios, self._stdin,
        )
        try:
            yield
        finally:
            restore_attrs(
                self._termios, self._stdin, self._saved_attrs,
            )
            self._saved_attrs = None
            self._active = False

    @contextmanager
    def for_input(self) -> Iterator[None]:
        """Temporarily restore echo for user input prompts."""
        if not self._active:
            yield
            return
        flush_and_restore(
            self._termios, self._stdin, self._saved_attrs,
        )
        try:
            yield
        finally:
            suppress_echo(self._termios, self._stdin)
