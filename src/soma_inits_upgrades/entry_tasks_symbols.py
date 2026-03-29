"""Per-entry analysis task: symbol extraction and usage search."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def task_symbols(ctx: EntryContext) -> bool:
    """Extract changed symbols and search for usages."""
    if ctx.entry_state.tasks_completed.get("symbols", False):
        return False

    from soma_inits_upgrades.processing_helpers import self_heal_resource
    from soma_inits_upgrades.state import mark_task_complete
    from soma_inits_upgrades.symbol_collection import extract_changed_symbols
    from soma_inits_upgrades.symbols import EMACS_DIR
    from soma_inits_upgrades.symbols_io import search_symbol_usages, write_usage_analysis

    diff_path = ctx.tmp_dir / f"{ctx.init_stem}.diff"
    if self_heal_resource(diff_path, "diff", ctx):
        return False
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    name = ctx.entry_state.init_file
    print(f"{label} {name}: extracting symbols and searching usages...", file=sys.stderr)
    symbols = extract_changed_symbols(diff_path)
    usage_path = ctx.tmp_dir / f"{ctx.init_stem}-usage-analysis.json"
    if not symbols:
        print(f"{label} {name}: no changed symbols, skipping usage search", file=sys.stderr)
        write_usage_analysis({}, usage_path)
    else:
        usages = search_symbol_usages(
            symbols, EMACS_DIR, ctx.output_dir, ctx.tmp_dir, run_fn=ctx.run_fn,
        )
        write_usage_analysis(usages, usage_path)
    mark_task_complete(ctx.entry_state, "symbols", ctx.entry_state_path)
    return False
