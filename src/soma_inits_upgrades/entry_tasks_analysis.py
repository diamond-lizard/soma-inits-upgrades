"""Per-entry analysis tasks: deps, version check, symbols, upgrade."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import EntryContext


def task_deps(ctx: EntryContext) -> bool:
    """Parse dependency metadata from the cloned repository."""
    if ctx.entry_state.tasks_completed.get("deps", False):
        return False
    from soma_inits_upgrades.deps import locate_package_metadata
    from soma_inits_upgrades.deps_processing import filter_dependencies, parse_requirements_sexp
    from soma_inits_upgrades.deps_resolution import determine_package_name
    from soma_inits_upgrades.git_ref_ops import ensure_working_tree_at_ref
    from soma_inits_upgrades.processing_helpers import self_heal_resource, set_entry_error
    from soma_inits_upgrades.state import atomic_write_json

    clone_dir = ctx.tmp_dir / ctx.init_stem
    if self_heal_resource(clone_dir, "clone", ctx):
        return False
    label = f"[{ctx.entry_idx}/{ctx.total}]"
    print(f"{label} {ctx.entry_state.init_file}: parsing dependencies...", file=sys.stderr)
    latest = ctx.entry_state.latest_ref or ""
    if not ensure_working_tree_at_ref(clone_dir, latest, run_fn=ctx.run_fn):
        set_entry_error(ctx, f"git checkout failed: latest_ref {ctx.entry_state.latest_ref}")
        return False
    raw_deps, pkg_name = locate_package_metadata(clone_dir)
    depends_on: list[str] = []
    min_emacs: str | None = None
    if raw_deps:
        parsed = parse_requirements_sexp(raw_deps)
        depends_on, min_emacs = filter_dependencies(parsed)
    ctx.entry_state.depends_on = depends_on
    ctx.entry_state.min_emacs_version = min_emacs
    ctx.entry_state.package_name = determine_package_name(pkg_name, ctx.entry_state.init_file)
    ctx.entry_state.tasks_completed["deps"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    return False


def task_version_check(ctx: EntryContext) -> bool:
    """Compare minimum Emacs version requirement against user's version."""
    if ctx.entry_state.tasks_completed.get("version_check", False):
        return False
    from soma_inits_upgrades.deps_resolution import requires_newer_emacs
    from soma_inits_upgrades.state import atomic_write_json

    ctx.entry_state.emacs_upgrade_required = requires_newer_emacs(
        ctx.entry_state.min_emacs_version, ctx.global_state.emacs_version,
    )
    ctx.entry_state.tasks_completed["version_check"] = True
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    return False


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


def _build_dep_context(ctx: EntryContext) -> str:
    """Build dependency context string for upgrade prompts."""
    from soma_inits_upgrades.prompts_upgrade import format_dependency_context
    return format_dependency_context(
        ctx.entry_state.depends_on or [],
        ctx.entry_state.min_emacs_version,
        ctx.entry_state.emacs_upgrade_required,
        ctx.global_state.emacs_version,
    )
