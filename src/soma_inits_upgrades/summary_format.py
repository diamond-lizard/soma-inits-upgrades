"""Summary formatting: completion message and category rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _format_elapsed(seconds: float) -> str:
    """Format elapsed seconds as 'Xm Ys' or 'Xs'."""
    if seconds >= 60:
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins}m {secs}s"
    return f"{int(seconds)}s"


def format_completion_message(
    categories: dict[str, list[str]], total: int,
    output_dir: Path, elapsed_seconds: float | None = None,
) -> str:
    """Format a multi-section completion message.

    Includes aggregate counts, categorized entry lists, output dir,
    and optional timing information.
    """
    done_count = len(categories.get("done", []))
    error_count = len(categories.get("errored", []))
    empty_count = len(categories.get("empty_diff", []))
    skip_count = len(categories.get("skipped", []))
    latest_count = len(categories.get("already_latest", []))
    partial_count = len(categories.get("partial", []))
    no_changes_count = len(categories.get("no_changes_needed", []))
    lines: list[str] = [
        f"Processed {total} entries: {done_count} completed, "
        f"{error_count} errors, {empty_count} empty diffs, "
        f"{skip_count} skipped, {latest_count} already latest, "
        f"{partial_count} partial, {no_changes_count} no changes needed",
    ]
    _append_category(lines, categories, "errored", "Errored entries")
    _append_category(lines, categories, "empty_diff", "Empty diff entries")
    _append_category(lines, categories, "skipped", "Skipped entries")
    _append_category(lines, categories, "already_latest", "Already latest entries")
    _append_category(lines, categories, "partial", "Partial results")
    _append_category(
        lines, categories, "no_changes_needed", "No changes needed",
    )
    lines.append(f"Output directory: {output_dir}")
    if elapsed_seconds is not None:
        lines.append(f"Completed in {_format_elapsed(elapsed_seconds)}")
    return "\n".join(lines)


def _append_category(
    lines: list[str], categories: dict[str, list[str]],
    key: str, label: str,
) -> None:
    """Append a category section to lines if non-empty."""
    items = categories.get(key, [])
    if not items:
        return
    lines.append(f"{label}:")
    lines.extend(f"  - {item}" for item in items)
