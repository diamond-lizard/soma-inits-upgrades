"""LLM pause infrastructure: prompt writing, display, clipboard, user interaction."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext, UserInputFn, XclipChecker


def write_prompt_file(text: str, path: Path) -> None:
    """Write prompt text to a file."""
    path.write_text(text, encoding="utf-8")


def display_llm_task_info(
    entry_idx: int, total: int, init_file: str,
    task_label: str, prompt_path: Path, output_path: Path,
) -> None:
    """Print LLM task progress info to stderr."""
    print(f"[{entry_idx}/{total}] {init_file}: {task_label}", file=sys.stderr)
    print(f"  Prompt: {prompt_path}", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)


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
            print(f"  Output file missing or empty: {output_path}", file=sys.stderr)
            continue
        if choice == "s":
            return "skip"
        if choice == "q":
            return "quit"
        print("Invalid choice", file=sys.stderr)


def llm_pause(
    text: str, prompt_path: Path, output_path: Path,
    entry_idx: int, total: int, init_file: str, task_label: str,
    xclip_checker: XclipChecker, input_fn: UserInputFn | None = None,
) -> str:
    """Orchestrate a single LLM pause point. Returns user action."""
    resolved_fn = input_fn if input_fn is not None else _default_input
    write_prompt_file(text, prompt_path)
    display_llm_task_info(entry_idx, total, init_file, task_label, prompt_path, output_path)
    offer_clipboard_copy(text, xclip_checker, resolved_fn)
    return prompt_user_action(output_path, resolved_fn)


def run_llm_task(
    ctx: EntryContext, task_name: str, prompt_fn: Callable[[], str],
    prompt_file: Path, output_file: Path,
    prerequisites: list[tuple[Path, str]],
    self_heal_fn: Callable[[Path, str, EntryContext], bool],
    task_label: str,
) -> str:
    """Shared LLM task lifecycle wrapper. Returns 'continue' or 'break'."""
    if ctx.entry_state.tasks_completed.get(task_name, False):
        return "continue"
    for prereq_path, creating_task in prerequisites:
        if self_heal_fn(prereq_path, creating_task, ctx):
            return "continue"
    prompt_text = prompt_fn()
    action = llm_pause(
        prompt_text, prompt_file, output_file,
        ctx.entry_idx, ctx.total, ctx.entry_state.init_file, task_label,
        ctx.xclip_checker, ctx.input_fn,
    )
    if action == "skip":
        from soma_inits_upgrades.processing_helpers import set_entry_done_early

        set_entry_done_early(ctx, "skipped", f"skipped by user at {task_label} step")
        return "break"
    if action == "quit":
        from soma_inits_upgrades.state import atomic_write_json

        atomic_write_json(ctx.entry_state_path, ctx.entry_state)
        atomic_write_json(ctx.global_state_path, ctx.global_state)
        sys.exit(0)
    from soma_inits_upgrades.state import mark_task_complete

    mark_task_complete(ctx.entry_state, task_name, ctx.entry_state_path)
    return "continue"
