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
