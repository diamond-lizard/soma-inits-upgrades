"""LLM pause infrastructure: prompt writing, display, clipboard, user interaction."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.prompts_helpers import shorten_home_in_text

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import UserInputFn, XclipChecker


def write_prompt_file(text: str, path: Path) -> None:
    """Write prompt text to a file."""
    path.write_text(text, encoding="utf-8")


def display_llm_task_info(
    entry_idx: int, total: int, init_file: str,
    task_label: str, prompt_path: Path, output_path: Path,
) -> None:
    """Print LLM task progress info to stderr."""
    print(f"[{entry_idx}/{total}] {init_file}: {task_label}", file=sys.stderr)
    short_prompt = shorten_home_in_text(str(prompt_path))
    short_output = shorten_home_in_text(str(output_path))
    print(f"  Prompt: {short_prompt}", file=sys.stderr)
    print(f"  Output: {short_output}", file=sys.stderr)


def offer_clipboard_copy(
    text: str, xclip_checker: XclipChecker,
    input_fn: UserInputFn | None = None,
) -> None:
    """Offer to copy prompt to X primary selection if xclip is available."""
    if not xclip_checker():
        return
    from soma_inits_upgrades.clipboard import copy_to_primary

    resolved_fn = input_fn if input_fn is not None else _default_input
    print("Press ENTER to copy prompt to X primary selection...", file=sys.stderr)
    resolved_fn("")
    copy_to_primary(text)
    print("Copied.", file=sys.stderr)


def _default_input(prompt: str) -> str:
    """Thin wrapper around input() for DI default."""
    return input(prompt)


def prompt_user_action(output_path: Path, input_fn: UserInputFn) -> str:
    """Prompt user to continue, skip, or quit. Returns action string."""
    while True:
        try:
            choice = input_fn("(c)ontinue, (s)kip, or (q)uit: ").strip().lower()
        except EOFError:
            return "quit"
        if choice in ("c", ""):
            if output_path.exists() and output_path.stat().st_size > 0:
                return "continue"
            short = shorten_home_in_text(str(output_path))
            print(f"  Output file missing or empty: {short}", file=sys.stderr)
            continue
        if choice == "s":
            return "skip"
        if choice == "q":
            return "quit"
        print("Invalid choice", file=sys.stderr)

