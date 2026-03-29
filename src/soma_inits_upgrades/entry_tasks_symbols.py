"""Per-entry analysis task: symbol extraction and usage search."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import RepoContext


def task_symbols(repo_ctx: RepoContext) -> bool:
    """Extract changed symbols and search for usages."""
    if repo_ctx.repo_state.tier1_tasks_completed.get("symbols", False):
        return False
    from soma_inits_upgrades.processing_helpers_repo import self_heal_repo_resource
    from soma_inits_upgrades.state import mark_repo_task_complete
    from soma_inits_upgrades.symbol_collection import extract_changed_symbols
    from soma_inits_upgrades.symbols import EMACS_DIR
    from soma_inits_upgrades.symbols_io import search_symbol_usages, write_usage_analysis
    ctx = repo_ctx.entry_ctx
    diff_path = repo_ctx.temp_dir / f"{ctx.init_stem}.diff"
    if self_heal_repo_resource(diff_path, "diff", repo_ctx):
        return False
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    name = ctx.entry_state.init_file
    print(f"{label} {name}: extracting symbols and searching usages...", file=sys.stderr)
    symbols = extract_changed_symbols(diff_path)
    usage_path = repo_ctx.temp_dir / f"{ctx.init_stem}-usage-analysis.json"
    if not symbols:
        print(f"{label} {name}: no changed symbols, skipping usage search", file=sys.stderr)
        write_usage_analysis({}, usage_path)
    else:
        usages = search_symbol_usages(
            symbols, EMACS_DIR, ctx.output_dir, repo_ctx.temp_dir, run_fn=ctx.run_fn,
        )
        write_usage_analysis(usages, usage_path)
    mark_repo_task_complete(
        ctx.entry_state, repo_ctx.repo_state, "symbols", ctx.entry_state_path,
    )
    return False
