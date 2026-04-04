"""LLM task lifecycle: pause orchestration and shared task wrapper."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext, UserInputFn, XclipChecker


def llm_pause(
    text: str, prompt_path: Path, output_path: Path,
    entry_idx: int, total: int, init_file: str, task_label: str,
    xclip_checker: XclipChecker, input_fn: UserInputFn | None = None,
) -> str:
    """Orchestrate a single LLM pause point. Returns user action."""
    from soma_inits_upgrades.llm_support import (
        display_llm_task_info,
        offer_clipboard_copy,
        prompt_user_action,
        write_prompt_file,
    )
    from soma_inits_upgrades.protocols import default_input
    resolved_fn = input_fn if input_fn is not None else default_input
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
