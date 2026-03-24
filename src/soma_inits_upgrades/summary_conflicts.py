"""Summary stage: Emacs version conflict identification and reporting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def identify_version_conflicts(
    graph: dict[str, dict[str, object]],
    entry_names: list[str],
    emacs_version: str,
) -> list[dict[str, str]]:
    """Identify entries requiring a newer Emacs than the user has.

    Filters graph entries to those in entry_names, checks each entry's
    min_emacs_version against the user's version.  Returns a list of
    dicts with keys 'package', 'min_emacs_version', 'user_version'.
    """
    from soma_inits_upgrades.deps_resolution import requires_newer_emacs

    conflicts: list[dict[str, str]] = []
    for name in entry_names:
        entry = graph.get(name)
        if entry is None:
            continue
        min_ver = entry.get("min_emacs_version")
        if not isinstance(min_ver, str):
            continue
        if requires_newer_emacs(min_ver, emacs_version):
            conflicts.append({
                "package": str(entry.get("package", name)),
                "min_emacs_version": min_ver,
                "user_version": emacs_version,
            })
    return conflicts


def format_version_conflicts_report(
    conflicts: list[dict[str, str]], emacs_version: str,
) -> str:
    """Format version conflicts into a markdown string.

    Lists each conflicting package with its required and user Emacs
    versions.  Returns an empty string if no conflicts.
    """
    if not conflicts:
        return ""
    lines: list[str] = [
        "# Emacs Version Conflicts",
        "",
        f"Your Emacs version: {emacs_version}",
        "",
        "The following packages require a newer Emacs:",
        "",
    ]
    for c in conflicts:
        pkg = c["package"]
        req = c["min_emacs_version"]
        lines.append(f"- **{pkg}**: requires Emacs {req}")
    lines.append("")
    return "\n".join(lines)


def write_version_conflicts(
    graph: dict[str, dict[str, object]],
    entry_names: list[str],
    emacs_version: str,
    output_path: Path,
) -> None:
    """Write the version conflicts report if any conflicts exist.

    Calls identify_version_conflicts, formats the report, and writes
    it to output_path.  Does not create the file if no conflicts.
    """
    conflicts = identify_version_conflicts(graph, entry_names, emacs_version)
    report = format_version_conflicts_report(conflicts, emacs_version)
    if report:
        output_path.write_text(report, encoding="utf-8")
