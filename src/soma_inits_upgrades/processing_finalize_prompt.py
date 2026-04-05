"""Error detail display and continue/quit prompt for failed entries."""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint_error
from soma_inits_upgrades.protocols import default_input

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext

_ORIGIN_RE = re.compile(r"\s*\[origin:\s*(.+)\]$")


def _print_repo_error(repo_url: str, state_path: str, notes: str) -> None:
    """Print one repo's error details in red with labeled prefixes."""
    eprint_error(f"repo: {repo_url}")
    eprint_error(f"state: {state_path}")
    match = _ORIGIN_RE.search(notes)
    if match:
        eprint_error(f"error location: {match.group(1)}")
        notes = notes[:match.start()]
    eprint_error(f"error: {notes}")


def prompt_on_all_repos_errored(ctx: EntryContext) -> None:
    """Print per-repo error details and prompt to continue or quit."""
    from soma_inits_upgrades.state import atomic_write_json
    resolved = ctx.input_fn if ctx.input_fn is not None else default_input
    for repo in ctx.entry_state.repos:
        if repo.done_reason != "error":
            continue
        _print_repo_error(repo.repo_url, str(ctx.entry_state_path), repo.notes or "")
    while True:
        choice = resolved("(c)ontinue or (q)uit: ").strip().lower()
        if choice == "q":
            atomic_write_json(ctx.entry_state_path, ctx.entry_state)
            atomic_write_json(ctx.global_state_path, ctx.global_state)
            sys.exit(0)
        if choice == "c":
            return
