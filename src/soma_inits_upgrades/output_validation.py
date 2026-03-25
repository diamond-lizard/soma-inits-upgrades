"""Output validation: file existence checks, content validation, malformed handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext

_REPORT_SECTIONS: list[str] = [
    "summary of changes",
    "breaking changes",
    "new dependencies",
    "removed or changed public api",
    "configuration impact",
    "emacs version",
    "recommended upgrade approach",
]


def validate_file_exists(
    path: Path, creating_task: str,
    self_heal_fn: Callable[[Path, str, EntryContext], bool],
    ctx: EntryContext,
) -> bool:
    """Check output file exists and is non-empty. Returns True if valid."""
    if path.exists() and path.stat().st_size > 0:
        return True
    self_heal_fn(path, creating_task, ctx)
    return False


def validate_security_review_content(
    path: Path, self_heal_fn: Callable[[Path, str, EntryContext], bool],
    ctx: EntryContext,
) -> bool:
    """Validate security review has a valid risk rating. Returns True if valid."""
    from soma_inits_upgrades.summary import extract_risk_rating

    rating = extract_risk_rating(path)
    if rating is not None and rating != "unknown":
        return True
    malformed = path.with_suffix(path.suffix + ".malformed")
    if path.exists():
        path.rename(malformed)
    self_heal_fn(path, "security_review", ctx)
    return False


def validate_upgrade_analysis_output(
    path: Path, self_heal_fn: Callable[[Path, str, EntryContext], bool],
    ctx: EntryContext,
) -> bool:
    """Validate and clean the upgrade analysis JSON. Returns True if valid."""
    from soma_inits_upgrades.validation_schema import UpgradeAnalysis, strip_code_fences

    if not path.exists():
        self_heal_fn(path, "upgrade_analysis", ctx)
        return False
    raw = path.read_text(encoding="utf-8")
    stripped = strip_code_fences(raw)
    try:
        UpgradeAnalysis.model_validate_json(stripped)
    except (ValueError, Exception):
        malformed = path.with_suffix(path.suffix + ".malformed")
        path.rename(malformed)
        self_heal_fn(path, "upgrade_analysis", ctx)
        return False
    if stripped != raw:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(stripped, encoding="utf-8")
        tmp.rename(path)
    return True


def validate_upgrade_report_content(
    path: Path, self_heal_fn: Callable[[Path, str, EntryContext], bool],
    ctx: EntryContext,
) -> bool:
    """Validate upgrade report contains required sections. Returns True if valid."""
    if not path.exists():
        self_heal_fn(path, "upgrade_report", ctx)
        return False
    text = path.read_text(encoding="utf-8").lower()
    found = sum(1 for s in _REPORT_SECTIONS if s in text)
    if found >= 2:
        return True
    malformed = path.with_suffix(path.suffix + ".malformed")
    path.rename(malformed)
    self_heal_fn(path, "upgrade_report", ctx)
    return False


def cleanup_malformed_files(output_dir: Path, init_file_name: str) -> None:
    """Delete leftover .malformed files for an entry."""
    init_stem = init_file_name.removesuffix(".el")
    patterns = [
        output_dir / f"{init_file_name}-security-review.md.malformed",
        output_dir / f"{init_file_name}-upgrade-process.md.malformed",
        output_dir / ".tmp" / f"{init_stem}-upgrade-analysis.json.malformed",
    ]
    for p in patterns:
        p.unlink(missing_ok=True)


def task_validate_outputs(ctx: EntryContext) -> bool:
    """Validate all expected output files exist and have valid content."""
    from soma_inits_upgrades.processing_helpers import self_heal_resource

    if ctx.entry_state.tasks_completed.get("validate_outputs", False):
        return False
    name = ctx.entry_state.init_file
    sec_path = ctx.output_dir / f"{name}-security-review.md"
    rpt_path = ctx.output_dir / f"{name}-upgrade-process.md"
    if not validate_file_exists(sec_path, "security_review", self_heal_resource, ctx):
        return False
    if not validate_file_exists(rpt_path, "upgrade_report", self_heal_resource, ctx):
        return False
    if not validate_security_review_content(sec_path, self_heal_resource, ctx):
        return False
    if not validate_upgrade_report_content(rpt_path, self_heal_resource, ctx):
        return False
    cleanup_malformed_files(ctx.output_dir, name)
    from soma_inits_upgrades.state import mark_task_complete

    mark_task_complete(ctx.entry_state, "validate_outputs", ctx.entry_state_path)
    return False
