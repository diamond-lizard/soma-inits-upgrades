"""Subprocess tracking: SubprocessRunner Protocol, ProcessTracker, tracked_run."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import SubprocessRunner


def _default_run(
    args: list[str] | str, **kwargs: object,
) -> subprocess.CompletedProcess[str]:
    """Thin wrapper around subprocess.run matching SubprocessRunner."""
    return subprocess.run(args, **kwargs)  # type: ignore[call-overload, no-any-return]


def resolve_run(run_fn: SubprocessRunner | None) -> SubprocessRunner:
    """Return run_fn or the default subprocess runner."""
    return run_fn if run_fn is not None else _default_run
