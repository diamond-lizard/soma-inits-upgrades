"""Security review prompt builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.prompts_helpers import (
    format_common_header,
    format_malformed_context,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import TypedDict

    class SecurityRepoInfo(TypedDict):
        """Per-repo descriptor for security review prompts."""

        package_name: str
        repo_url: str
        pinned_ref: str
        latest_ref: str
        diff_path: Path


def generate_security_review_prompt(
    repos: Sequence[SecurityRepoInfo],
    output_path: Path,
    malformed_report_path: Path | None = None,
) -> str:
    """Generate the LLM prompt for a security review of package changes.

    Accepts a list of per-repo descriptors. Each descriptor provides
    the package name, repo URL, refs, and diff file path. With a single
    repo the output is functionally equivalent to the original format.
    """
    repo_parts: list[str] = []
    for repo in repos:
        hdr = format_common_header(
            repo["package_name"], repo["repo_url"],
            repo["pinned_ref"], repo["latest_ref"],
        )
        repo_parts.append(f"{hdr}Diff file: {repo['diff_path']}\n")
    repos_section = "\n".join(repo_parts)
    malformed = format_malformed_context(
        malformed_report_path,
        "the previous output was rejected because it lacked "
        "a valid Risk Rating line",
        "produce a corrected version that preserves the existing "
        "analysis while adding the required Risk Rating line "
        "in the exact specified format",
    )
    focus = (
        "- shell-command, call-process, start-process calls\n"
        "- eval, load, require of unknown packages\n"
        "- Network access (url-retrieve, request, etc.)\n"
        "- File system write operations\n"
        "- advice-add or defadvice usage\n"
        "- Compilation of external code\n"
        "- Obfuscated or encoded content\n"
    )
    fmt = (
        "The report MUST include:\n"
        "1. A title line identifying the package and repository\n"
        "2. A line in EXACTLY this format: "
        "`Risk Rating: <rating>`\n"
        "   where <rating> is one of: low, medium, high, critical\n"
        "   (lowercase, no other values, no additional text "
        "on the line)\n"
        "3. The pinned ref and latest ref SHAs\n"
        "4. A freeform narrative overview of security-relevant "
        "changes\n"
        "5. NO code snippets, diff excerpts, or line numbers\n"
    )
    return (
        f"# Security Review Task\n\n{repos_section}{malformed}\n"
        f"## Instructions\nReview ALL changes for security "
        f"concerns, focusing on:\n{focus}\n"
        f"## Required Output Format\n"
        f"Write your review to: {output_path}\n\n{fmt}"
    )
