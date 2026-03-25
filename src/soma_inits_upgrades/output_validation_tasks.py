"""Output validation tasks: report validation, malformed cleanup, task handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext


def validate_upgrade_report_content(
    path: Path, self_heal_fn: Callable[[Path, str, EntryContext], bool],
    ctx: EntryContext,
) -> bool:
    """Validate upgrade report contains required sections. Returns True if valid."""
    from soma_inits_upgrades.output_validation import _REPORT_SECTIONS
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
    from soma_inits_upgrades.output_validation import (
        validate_file_exists,
        validate_security_review_content,
    )
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
