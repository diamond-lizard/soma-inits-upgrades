"""Shared prompt formatting helpers for LLM prompt builders."""

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


def format_dependency_context(
    depends_on: list[str],
    min_emacs_version: str | None,
    emacs_upgrade_required: bool,
    emacs_version: str,
) -> str:
    """Format dependency and Emacs version info for inclusion in prompts."""
    parts: list[str] = ["\n## Dependency and Version Context\n"]
    if depends_on:
        parts.append(f"Non-built-in dependencies: {', '.join(depends_on)}\n")
    else:
        parts.append("Non-built-in dependencies: none\n")
    if min_emacs_version:
        parts.append(
            f"Minimum Emacs version required: {min_emacs_version}\n",
        )
    parts.append(f"User's current Emacs version: {emacs_version}\n")
    if emacs_upgrade_required:
        parts.append(
            "WARNING: This package requires a newer Emacs version.\n",
        )
    return "".join(parts)


def format_preamble(task_description: str) -> str:
    """Return a contextual preamble for an LLM prompt.

    *task_description* is a short phrase such as "performing a security
    review of" or "writing an upgrade report for".  The preamble
    explains the user's workflow so the LLM has enough context to
    reason about its task.
    """
    return (
        "You will be given the task of "
        f"{task_description} changes to one or more\n"
        "Emacs packages. The context of this review is as follows: "
        "The user manages their\n"
        "Emacs packages using elpaca, which pins each package to a "
        "specific git commit. Over\n"
        "time these pins become stale as upstream repositories "
        "receive new commits. The user is\n"
        "using a tool that identifies stale pins and generates diffs "
        "between the pinned commit\n"
        "and the latest upstream commit so that the changes can be "
        "reviewed before the user\n"
        "decides whether to update each pin.\n\n"
    )
