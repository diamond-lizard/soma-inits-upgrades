"""Rich console foundation for colored stderr output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from typing import Any

stderr_console = Console(stderr=True)


def eprint(*args: Any, **kwargs: Any) -> None:
    """Print to stderr via the rich Console."""
    stderr_console.print(*args, **kwargs)
