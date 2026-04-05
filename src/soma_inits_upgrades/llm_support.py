"""LLM pause infrastructure: prompt writing, display, clipboard, user interaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint, eprint_error, eprint_prompt
from soma_inits_upgrades.prompts_helpers import shorten_home_in_text
from soma_inits_upgrades.protocols import default_input

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
    eprint(f"[{entry_idx}/{total}] {init_file}: {task_label}")
    short_prompt = shorten_home_in_text(str(prompt_path))
    short_output = shorten_home_in_text(str(output_path))
    eprint(f"  Prompt: {short_prompt}")
    eprint(f"  Output: {short_output}")


def offer_clipboard_copy(
    text: str, xclip_checker: XclipChecker,
    input_fn: UserInputFn | None = None,
) -> None:
    """Offer to copy prompt to X primary selection if xclip is available."""
    if not xclip_checker():
        return
    from soma_inits_upgrades.clipboard import copy_to_primary

    resolved_fn = input_fn if input_fn is not None else default_input
    eprint_prompt("Press ENTER to copy prompt to X primary selection...")
    resolved_fn("")
    copy_to_primary(text)
    eprint("Copied.")


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
            eprint_error(f"  Output file missing or empty: {short}")
            continue
        if choice == "s":
            return "skip"
        if choice == "q":
            return "quit"
        eprint_error("Invalid choice")

