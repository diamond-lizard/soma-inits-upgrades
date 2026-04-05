"""Error detail display and continue/quit prompt for failed entries."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from soma_inits_upgrades.protocols import default_input

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def prompt_on_all_repos_errored(ctx: EntryContext) -> None:
    """Print per-repo error details and prompt to continue or quit."""
    from soma_inits_upgrades.state import atomic_write_json
    resolved = ctx.input_fn if ctx.input_fn is not None else default_input
    for repo in ctx.entry_state.repos:
        if repo.done_reason != "error":
            continue
        print(repo.repo_url, file=sys.stderr)
        print(str(ctx.entry_state_path), file=sys.stderr)
        print(repo.notes or "", file=sys.stderr)
    while True:
        choice = resolved("(c)ontinue or (q)uit: ").strip().lower()
        if choice == "q":
            atomic_write_json(ctx.entry_state_path, ctx.entry_state)
            atomic_write_json(ctx.global_state_path, ctx.global_state)
            sys.exit(0)
        if choice == "c":
            return
