"""Rich console and ANSI-colored stderr output functions."""

from __future__ import annotations

import atexit
import os
import sys
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from typing import IO

stderr_console = Console(stderr=True)

_RED = "31"
_YELLOW = "33"
_BLUE = "34"
_GREEN = "32"

_color_emitted = False


def _should_color() -> bool:
    """Return True when ANSI color codes should be emitted."""
    if "NO_COLOR" in os.environ:
        return False
    if "FORCE_COLOR" in os.environ:
        return True
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def _colorize(text: str, code: str) -> str:
    """Wrap text in ANSI escape codes if color is enabled."""
    global _color_emitted
    if not _should_color():
        return text
    _color_emitted = True
    return f"\033[{code}m{text}\033[0m"


def _reset_terminal_color(_stderr: IO[str] | None = None) -> None:
    """Write ANSI reset to stderr if color was used during this run."""
    stream = _stderr if _stderr is not None else sys.stderr
    if not _color_emitted:
        return
    if not (hasattr(stream, "isatty") and stream.isatty()):
        return
    stream.write("\033[0m")
    stream.flush()


atexit.register(_reset_terminal_color)


def eprint_error(*args: object, end: str = "\n", flush: bool = False) -> None:
    """Print a red error message to stderr."""
    text = " ".join(str(a) for a in args)
    print(_colorize(text, _RED), file=sys.stderr, end=end, flush=flush)


def eprint_warn(*args: object, end: str = "\n", flush: bool = False) -> None:
    """Print a yellow warning message to stderr."""
    text = " ".join(str(a) for a in args)
    print(_colorize(text, _YELLOW), file=sys.stderr, end=end, flush=flush)


def eprint_prompt(*args: object, end: str = "\n", flush: bool = False) -> None:
    """Print a blue prompt message to stderr."""
    text = " ".join(str(a) for a in args)
    print(_colorize(text, _BLUE), file=sys.stderr, end=end, flush=flush)


def eprint_plain(*args: object, end: str = "\n", flush: bool = False) -> None:
    """Print an uncolored message to stderr."""
    text = " ".join(str(a) for a in args)
    print(text, file=sys.stderr, end=end, flush=flush)


def eprint(*args: object, end: str = "\n", flush: bool = False) -> None:
    """Print a green status message to stderr."""
    text = " ".join(str(a) for a in args)
    print(_colorize(text, _GREEN), file=sys.stderr, end=end, flush=flush)
