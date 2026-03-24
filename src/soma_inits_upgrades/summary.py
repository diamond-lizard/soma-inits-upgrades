"""Summary stage: security summary compilation, version conflict listing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_RISK_PATTERN: re.Pattern[str] = re.compile(
    r"^Risk\s+Rating:\s*(.+)$", re.IGNORECASE | re.MULTILINE,
)

_VALID_RATINGS: frozenset[str] = frozenset(
    {"critical", "high", "medium", "low"},
)


def extract_risk_rating(file_path: Path) -> str | None:
    """Read a security review report and extract its risk rating.

    Returns the lowercase rating string ('critical', 'high', 'medium',
    'low') if found.  Returns None if the file does not exist.
    Returns 'unknown' if the file exists but has no parseable rating.
    """
    if not file_path.exists():
        return None
    text = file_path.read_text(encoding="utf-8")
    match = _RISK_PATTERN.search(text)
    if match is None:
        return "unknown"
    rating = match.group(1).strip().lower()
    if rating in _VALID_RATINGS:
        return rating
    return "unknown"


def group_entries_by_rating(
    entries: list[tuple[str, str]],
) -> dict[str, list[str]]:
    """Group init file names by their risk rating.

    Takes (init_file_name, rating) pairs and returns a dict mapping
    each rating string to a list of file basenames.
    """
    grouped: dict[str, list[str]] = {}
    for name, rating in entries:
        grouped.setdefault(rating, []).append(name)
    return grouped


def compile_security_summary(
    entry_names: list[str], output_dir: Path,
) -> dict[str, list[str]]:
    """Compile security review ratings for all entries.

    Iterates entry_names, reads each security review file, extracts
    the risk rating, filters out entries with no file (None rating),
    and groups the rest by rating.
    """
    pairs: list[tuple[str, str]] = []
    for name in entry_names:
        path = output_dir / f"{name}-security-review.md"
        rating = extract_risk_rating(path)
        if rating is None:
            continue
        pairs.append((name, rating))
    return group_entries_by_rating(pairs)


_SEVERITY_ORDER: list[str] = [
    "critical", "high", "medium", "low", "unknown",
]


def write_security_summary_report(
    grouped: dict[str, list[str]], output_path: Path,
) -> None:
    """Write the security summary markdown file.

    Lists packages under headings for each risk level in severity
    order: Critical, High, Medium, Low, Unknown.  Skips empty groups.
    """
    lines: list[str] = ["# Security Review Summary", ""]
    for rating in _SEVERITY_ORDER:
        packages = grouped.get(rating)
        if not packages:
            continue
        lines.append(f"## {rating.title()}")
        lines.append("")
        for pkg in packages:
            lines.append(f"- {pkg}")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


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
