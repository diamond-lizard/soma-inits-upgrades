"""LLM prompt template for the upgrade report."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.prompts_helpers import (
    format_common_header,
    format_malformed_context,
    format_preamble,
    shorten_home_in_text,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import TypedDict

    class ReportRepoInfo(TypedDict):
        """Per-repo descriptor for upgrade report prompts."""

        package_name: str
        repo_url: str
        pinned_ref: str
        latest_ref: str


def generate_upgrade_report_prompt(
    repos: Sequence[ReportRepoInfo],
    upgrade_analysis_path: Path,
    output_path: Path,
    dependency_context: str,
    malformed_report_path: Path | None = None,
) -> str:
    """Generate the LLM prompt for writing the upgrade process report.

    Accepts a list of per-repo descriptors. The prompt instructs the
    LLM to produce a single coherent report covering all packages.
    With a single repo the output is functionally equivalent to the
    original format.
    """
    repo_parts: list[str] = []
    for repo in repos:
        repo_parts.append(format_common_header(
            repo["package_name"], repo["repo_url"],
            repo["pinned_ref"], repo["latest_ref"],
        ))
    repos_section = "\n".join(repo_parts)
    malformed = format_malformed_context(
        malformed_report_path,
        "the previous output was rejected because it lacked the "
        "required report sections",
        "produce a corrected version with all required sections: "
        "Summary of Changes, Breaking Changes, New Dependencies, "
        "Removed or Changed Public API, Configuration Impact "
        "Analysis, Emacs Version Requirement, and Recommended "
        "Upgrade Approach",
    )
    sections = (
        "1. Summary of Changes\n"
        "2. Breaking Changes\n"
        "3. New Dependencies\n"
        "4. Removed or Changed Public API "
        "(reference affected user config files)\n"
        "5. Configuration Impact Analysis (per affected file)\n"
        "6. Emacs Version Requirement (if applicable)\n"
        "7. Recommended Upgrade Approach\n"
    )
    preamble = format_preamble("writing an upgrade report for")
    return shorten_home_in_text(
        f"{preamble}"
        f"# Upgrade Report Task\n\n"
        f"{repos_section}{dependency_context}{malformed}\n"
        f"## Instructions\n"
        f"Read the upgrade analysis at: {upgrade_analysis_path}\n\n"
        f"## Required Output\n"
        f"Write a markdown report to: {output_path}\n\n"
        f"The report MUST include these sections:\n{sections}\n"
        "NO code snippets, diff excerpts, or line numbers.\n"
    )
