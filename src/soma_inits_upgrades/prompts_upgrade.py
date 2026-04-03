"""LLM prompt template for upgrade analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.prompts_helpers import (
    format_common_header,
    format_malformed_context,
    format_preamble,
    shorten_home_in_text,
)
from soma_inits_upgrades.prompts_unverified_warning import (
    build_unverified_warning,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import TypedDict

    class AnalysisRepoInfo(TypedDict):
        """Per-repo descriptor for upgrade analysis prompts."""

        package_name: str
        repo_url: str
        pinned_ref: str
        latest_ref: str
        diff_path: Path
        usage_path: Path


def generate_upgrade_analysis_prompt(
    repos: Sequence[AnalysisRepoInfo],
    output_path: Path,
    dependency_context: str,
    malformed_analysis_path: Path | None = None,
) -> str:
    """Generate the LLM prompt for upgrade analysis producing JSON output.

    Accepts a list of per-repo descriptors. Each provides the package
    name, repo URL, refs, diff file path, and usage analysis path.
    With a single repo the output is functionally equivalent to the
    original format.
    """
    from soma_inits_upgrades.validation_schema import UpgradeAnalysis

    repo_parts: list[str] = []
    for repo in repos:
        hdr = format_common_header(
            repo["package_name"], repo["repo_url"],
            repo["pinned_ref"], repo["latest_ref"],
        )
        warning = build_unverified_warning(repo["usage_path"])
        repo_parts.append(
            f"{hdr}Diff file: {repo['diff_path']}\n"
            f"Usage analysis: {repo['usage_path']}\n"
            f"{warning}",
        )
    repos_section = "\n".join(repo_parts)
    schema = UpgradeAnalysis.model_json_schema()
    malformed = format_malformed_context(
        malformed_analysis_path,
        "the previous output was rejected because it was not valid "
        "JSON conforming to the required schema",
        "(1) read and examine the malformed file to determine whether "
        "it contains useful analysis that can be preserved, (2) either "
        "fix the malformed output (correcting JSON syntax errors, "
        "adding missing fields, adjusting types) if the content is "
        "substantially correct, or use it as a reference when "
        "producing a fresh analysis if the content is too broken to "
        "repair, and (3) ensure the corrected output is valid JSON "
        "conforming to the provided schema, written to the specified "
        "output path",
    )
    preamble = format_preamble(
        "performing an upgrade analysis of",
    )
    return shorten_home_in_text(
        f"{preamble}"
        f"# Upgrade Analysis Task\n\n"
        f"{repos_section}{dependency_context}{malformed}\n"
        f"## Instructions\n"
        f"Read the diff and usage analysis files listed above.\n\n"
        f"### Understanding the Usage Analysis\n"
        f"The usage analysis file maps each elisp symbol that was removed or\n"
        f"modified in the upstream diff to the files in the user's Emacs\n"
        f"configuration (~/.emacs.d/) that reference it. This tells you which\n"
        f"changes actually affect the user:\n"
        f"- A symbol mapping to one or more files means those config files\n"
        f"  depend on it and may need attention.\n"
        f"- A symbol mapping to an empty list means nothing in the user's\n"
        f"  config references it, so the change is unlikely to affect them.\n"
        f"- An entirely empty dictionary means no definition-level symbol\n"
        f"  changes were detected in the diff.\n\n"
        f"## Required Output\n"
        f"Write a JSON file to: {output_path}\n\n"
        f"The JSON must conform to this schema:\n"
        f"```json\n{schema}\n```\n"
    )
