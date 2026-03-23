"""LLM prompt templates for upgrade analysis and upgrade report."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts import format_common_header, format_malformed_context


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
        parts.append(f"Minimum Emacs version required: {min_emacs_version}\n")
    parts.append(f"User's current Emacs version: {emacs_version}\n")
    if emacs_upgrade_required:
        parts.append("WARNING: This package requires a newer Emacs version.\n")
    return "".join(parts)


def generate_upgrade_analysis_prompt(
    package_name: str,
    repo_url: str,
    pinned_ref: str,
    latest_ref: str,
    diff_path: Path,
    usage_analysis_path: Path,
    output_path: Path,
    dependency_context: str,
    malformed_analysis_path: Path | None = None,
) -> str:
    """Generate the LLM prompt for upgrade analysis producing JSON output.

    Returns the full prompt string directing the LLM to produce a JSON
    file conforming to the UpgradeAnalysis schema.
    """
    from soma_inits_upgrades.validation_schema import UpgradeAnalysis

    header = format_common_header(package_name, repo_url, pinned_ref, latest_ref)
    schema = UpgradeAnalysis.model_json_schema()
    malformed = format_malformed_context(
        malformed_analysis_path,
        "the previous output was rejected because it was not valid JSON "
        "conforming to the required schema",
        "(1) read and examine the malformed file to determine whether it "
        "contains useful analysis that can be preserved, (2) either fix "
        "the malformed output (correcting JSON syntax errors, adding missing "
        "fields, adjusting types) if the content is substantially correct, "
        "or use it as a reference when producing a fresh analysis if the "
        "content is too broken to repair, and (3) ensure the corrected "
        "output is valid JSON conforming to the provided schema, written "
        "to the specified output path",
    )
    return (
        f"# Upgrade Analysis Task\n\n{header}{dependency_context}{malformed}\n"
        f"## Instructions\nRead the diff file at: {diff_path}\n"
        f"Read the usage analysis at: {usage_analysis_path}\n\n"
        f"## Required Output\nWrite a JSON file to: {output_path}\n\n"
        f"The JSON must conform to this schema:\n```json\n{schema}\n```\n"
    )
