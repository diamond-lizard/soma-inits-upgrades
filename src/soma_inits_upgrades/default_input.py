"""Default user-input fallback for DI injection."""

from __future__ import annotations


def default_input(prompt: str) -> str:
    """Safety-net UserInputFn fallback when no input_fn is injected.

    In production the composition root injects an echo-managed
    closure instead.
    """
    return input(prompt)
