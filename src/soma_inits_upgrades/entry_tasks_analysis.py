"""Per-entry analysis tasks: security review, deps, version check, symbols, upgrade."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.graph import GraphDict
    from soma_inits_upgrades.protocols import EntryContext


def task_security_review(ctx: EntryContext) -> bool:
    """Run the security review LLM pause."""
    from soma_inits_upgrades.llm_support import run_llm_task
    from soma_inits_upgrades.processing_helpers import self_heal_resource
    from soma_inits_upgrades.prompts import generate_security_review_prompt

    name = ctx.entry_state.init_file
    diff_path = ctx.tmp_dir / f"{ctx.init_stem}.diff"
    output_path = ctx.output_dir / f"{name}-security-review.md"
    prompt_path = ctx.tmp_dir / f"{ctx.init_stem}-security-review.prompt.md"
    malformed = output_path.with_suffix(output_path.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    pkg = ctx.entry_state.package_name or ctx.init_stem

    def prompt_fn() -> str:
        return generate_security_review_prompt(
            pkg, ctx.entry_state.repo_url, ctx.entry_state.pinned_ref,
            ctx.entry_state.latest_ref or "", diff_path, output_path,
            malformed_report_path=mal_arg,
        )

    result = run_llm_task(
        ctx, "security_review", prompt_fn, prompt_path, output_path,
        [(diff_path, "diff")], self_heal_resource, "Security Review",
    )
    return result == "break"


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


def task_upgrade_analysis(ctx: EntryContext) -> bool:
    """Run the upgrade analysis LLM pause and validate output."""
    from soma_inits_upgrades.llm_support import run_llm_task
    from soma_inits_upgrades.output_validation import validate_upgrade_analysis_output
    from soma_inits_upgrades.processing_helpers import self_heal_resource
    from soma_inits_upgrades.prompts_upgrade import generate_upgrade_analysis_prompt

    diff_path = ctx.tmp_dir / f"{ctx.init_stem}.diff"
    usage_path = ctx.tmp_dir / f"{ctx.init_stem}-usage-analysis.json"
    output_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.json"
    prompt_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.prompt.md"
    malformed = output_path.with_suffix(output_path.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    dep_ctx = _build_dep_context(ctx)
    pkg = ctx.entry_state.package_name or ctx.init_stem

    def prompt_fn() -> str:
        return generate_upgrade_analysis_prompt(
            pkg, ctx.entry_state.repo_url, ctx.entry_state.pinned_ref,
            ctx.entry_state.latest_ref or "", diff_path, usage_path,
            output_path, dep_ctx, malformed_analysis_path=mal_arg,
        )

    result = run_llm_task(
        ctx, "upgrade_analysis", prompt_fn, prompt_path, output_path,
        [(diff_path, "diff"), (usage_path, "symbols")],
        self_heal_resource, "Upgrade Analysis",
    )
    if result == "break":
        return True
    is_done = ctx.entry_state.tasks_completed.get("upgrade_analysis", False)
    if is_done and not validate_upgrade_analysis_output(
        output_path, self_heal_resource, ctx,
    ):
        ctx.entry_state.tasks_completed["upgrade_analysis"] = False
    return False


def task_upgrade_report(ctx: EntryContext) -> bool:
    """Run the upgrade report LLM pause."""
    from soma_inits_upgrades.llm_support import run_llm_task
    from soma_inits_upgrades.processing_helpers import self_heal_resource
    from soma_inits_upgrades.prompts_report import generate_upgrade_report_prompt

    name = ctx.entry_state.init_file
    analysis_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-analysis.json"
    output_path = ctx.output_dir / f"{name}-upgrade-process.md"
    prompt_path = ctx.tmp_dir / f"{ctx.init_stem}-upgrade-report.prompt.md"
    malformed = output_path.with_suffix(output_path.suffix + ".malformed")
    mal_arg = malformed if malformed.exists() else None
    dep_ctx = _build_dep_context(ctx)
    pkg = ctx.entry_state.package_name or ctx.init_stem

    def prompt_fn() -> str:
        return generate_upgrade_report_prompt(
            pkg, ctx.entry_state.repo_url, ctx.entry_state.pinned_ref,
            ctx.entry_state.latest_ref or "", analysis_path,
            output_path, dep_ctx, malformed_report_path=mal_arg,
        )

    result = run_llm_task(
        ctx, "upgrade_report", prompt_fn, prompt_path, output_path,
        [(analysis_path, "upgrade_analysis")],
        self_heal_resource, "Upgrade Report",
    )
    return result == "break"


def recover_single_graph_entry(
    init_file: str, graph: GraphDict, state_dir: Path,
    results: list[dict[str, str]], output_dir: Path,
) -> bool:
    """Recover a single entry's graph data. Returns True if rerun needed."""
    from soma_inits_upgrades.state import read_entry_state
    from soma_inits_upgrades.state_lifecycle import create_entry_state_if_missing

    path = state_dir / f"{init_file}.json"
    state = read_entry_state(path)
    if state is not None and state.package_name is not None:
        from soma_inits_upgrades.graph import add_entry

        add_entry(
            graph, init_file, state.package_name,
            state.min_emacs_version, state.depends_on or [],
        )
        return False
    entry_dict = next((e for e in results if e["init_file"] == init_file), None)
    if entry_dict:
        create_entry_state_if_missing(entry_dict, state_dir)
    import pathlib

    prog = pathlib.Path(sys.argv[0]).name
    print(
        f"Warning: state file corrupt for {init_file}, recreating. "
        f"This entry will be fully reprocessed on the next run of {prog}.",
        file=sys.stderr,
    )
    return True


def recover_graph_from_backup(
    graph: GraphDict, results: list[dict[str, str]],
    state_dir: Path, output_dir: Path,
) -> tuple[GraphDict, bool]:
    """Rebuild missing graph entries from state files. Returns (graph, needs_rerun)."""
    from soma_inits_upgrades.state import read_entry_state

    needs_rerun = False
    for entry in results:
        name = entry["init_file"]
        state = read_entry_state(state_dir / f"{name}.json")
        if state is None or not state.tasks_completed.get("graph_update", False):
            continue
        if name in graph:
            continue
        if recover_single_graph_entry(name, graph, state_dir, results, output_dir):
            needs_rerun = True
    return graph, needs_rerun


def task_graph_update(ctx: EntryContext) -> bool:
    """Update the dependency graph with this entry's data."""
    if ctx.entry_state.tasks_completed.get("graph_update", False):
        return False
    from soma_inits_upgrades.graph import add_entry, read_graph, write_graph
    from soma_inits_upgrades.processing_helpers import set_entry_error
    from soma_inits_upgrades.state import mark_task_complete

    graph_path = ctx.output_dir / "soma-inits-dependency-graphs.json"
    graph, restored = read_graph(graph_path)
    needs_rerun = False
    if restored:
        graph, needs_rerun = recover_graph_from_backup(
            graph, ctx.results, ctx.state_dir, ctx.output_dir,
        )
    pkg = ctx.entry_state.package_name or ctx.init_stem
    add_entry(graph, ctx.entry_state.init_file, pkg,
              ctx.entry_state.min_emacs_version, ctx.entry_state.depends_on or [])
    try:
        write_graph(graph_path, graph)
    except OSError as exc:
        set_entry_error(ctx, f"failed to update dependency graph: {exc}")
        return needs_rerun
    mark_task_complete(ctx.entry_state, "graph_update", ctx.entry_state_path)
    return needs_rerun
