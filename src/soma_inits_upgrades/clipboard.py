#!/usr/bin/env python3
"""xclip detection and X primary selection copy."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint_warn

if TYPE_CHECKING:
    from collections.abc import Callable

    from soma_inits_upgrades.protocols import WhichFn


def make_xclip_checker(
    which_fn: WhichFn | None = None,
) -> Callable[[], bool]:
    """Return a closure that checks xclip availability, caching the result.

    The closure calls which_fn('xclip') on first invocation and caches the
    boolean result, returning the cached value on subsequent calls.
    """
    resolved_fn = which_fn if which_fn is not None else shutil.which
    cache: list[bool] = []

    def checker() -> bool:
        """Return True if xclip is available on the system."""
        if not cache:
            cache.append(resolved_fn("xclip") is not None)
        return cache[0]

    return checker


def copy_to_primary(
    text: str,
    run_fn: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Copy text to the X primary selection using xclip.

    Only call after verifying xclip is available. Handles xclip failure
    gracefully by printing a warning to stderr.
    """
    try:
        run_fn(
            ["xclip", "-selection", "primary"],
            input=text,
            text=True,
            check=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        eprint_warn(f"Warning: failed to copy to clipboard: {exc}")
