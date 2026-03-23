"""LLM prompt helpers and security review prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def format_common_header(
    package_name: str, repo_url: str, pinned_ref: str, latest_ref: str,
) -> str:
    """Format common context into a standard header block for LLM prompts.

    Includes package name, repo URL, pinned/latest refs, and diff direction.
    """
    return (
        f"## Package: {package_name}\n"
        f"Repository: {repo_url}\n"
        f"Pinned ref: {pinned_ref}\n"
        f"Latest ref: {latest_ref}\n\n"
        f"The diff was generated with `git diff {pinned_ref} {latest_ref}`. "
        "Lines prefixed with `-` are from the OLD pinned version; "
        "lines prefixed with `+` are from the NEW latest version.\n"
    )


def format_malformed_context(
    malformed_path: Path | None,
    rejection_reason: str,
    correction_instructions: str,
) -> str:
    """Format a malformed-file context section for inclusion in a prompt.

    Returns an empty string if malformed_path is None or does not exist.
    """
    if malformed_path is None or not malformed_path.exists():
        return ""
    return (
        f"\n## Previous Attempt (Rejected)\n"
        f"A previous attempt is saved at: {malformed_path}\n"
        f"Rejection reason: {rejection_reason}\n"
        f"Instructions: {correction_instructions}\n"
    )


def generate_security_review_prompt(
    package_name: str,
    repo_url: str,
    pinned_ref: str,
    latest_ref: str,
    diff_path: Path,
    output_path: Path,
    malformed_report_path: Path | None = None,
) -> str:
    """Generate the LLM prompt for a security review of package changes.

    Returns the full prompt string including task description, security
    focus areas, required output format, and file paths.
    """
    header = format_common_header(package_name, repo_url, pinned_ref, latest_ref)
    malformed = format_malformed_context(
        malformed_report_path,
        "the previous output was rejected because it lacked a valid Risk Rating line",
        "produce a corrected version that preserves the existing analysis "
        "while adding the required Risk Rating line in the exact specified format",
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
        "2. A line in EXACTLY this format: `Risk Rating: <rating>`\n"
        "   where <rating> is one of: low, medium, high, critical\n"
        "   (lowercase, no other values, no additional text on the line)\n"
        "3. The pinned ref and latest ref SHAs\n"
        "4. A freeform narrative overview of security-relevant changes\n"
        "5. NO code snippets, diff excerpts, or line numbers\n"
    )
    return (
        f"# Security Review Task\n\n{header}{malformed}\n"
        f"## Instructions\nRead the diff file at: {diff_path}\n\n"
        f"Review ALL changes for security concerns, focusing on:\n{focus}\n"
        f"## Required Output Format\nWrite your review to: {output_path}\n\n{fmt}"
    )
