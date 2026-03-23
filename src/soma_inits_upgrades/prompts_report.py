"""LLM prompt template for the upgrade report."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts import format_common_header, format_malformed_context


def generate_upgrade_report_prompt(
    package_name: str,
    repo_url: str,
    pinned_ref: str,
    latest_ref: str,
    upgrade_analysis_path: Path,
    output_path: Path,
    dependency_context: str,
    malformed_report_path: Path | None = None,
) -> str:
    """Generate the LLM prompt for writing the upgrade process report.

    Returns the full prompt string directing the LLM to write a markdown
    report with all required sections.
    """
    header = format_common_header(package_name, repo_url, pinned_ref, latest_ref)
    malformed = format_malformed_context(
        malformed_report_path,
        "the previous output was rejected because it lacked the required "
        "report sections",
        "produce a corrected version with all required sections: Summary "
        "of Changes, Breaking Changes, New Dependencies, Removed or Changed "
        "Public API, Configuration Impact Analysis, Emacs Version "
        "Requirement, and Recommended Upgrade Approach",
    )
    sections = (
        "1. Summary of Changes\n"
        "2. Breaking Changes\n"
        "3. New Dependencies\n"
        "4. Removed or Changed Public API (reference affected user config files)\n"
        "5. Configuration Impact Analysis (per affected file)\n"
        "6. Emacs Version Requirement (if applicable)\n"
        "7. Recommended Upgrade Approach\n"
    )
    return (
        f"# Upgrade Report Task\n\n{header}{dependency_context}{malformed}\n"
        f"## Instructions\nRead the upgrade analysis at: {upgrade_analysis_path}\n\n"
        f"## Required Output\nWrite a markdown report to: {output_path}\n\n"
        f"The report MUST include these sections:\n{sections}\n"
        "NO code snippets, diff excerpts, or line numbers.\n"
    )
