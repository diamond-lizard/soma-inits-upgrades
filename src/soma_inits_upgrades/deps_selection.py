"""Package candidate selection for monorepo disambiguation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from soma_inits_upgrades.console import eprint_error, eprint_prompt
from soma_inits_upgrades.protocols import default_input

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import UserInputFn


@dataclass
class PackageCandidate:
    """A single package candidate from a repository."""

    stem: str
    path: Path
    source_type: str
    header_line: int | None
    embedded_name: str | None
    raw_deps: str | None



def compute_suggested_index(
    candidates: list[PackageCandidate], init_file: str | None,
) -> int:
    """Compute suggested candidate index via two-tier fallback.

    1. Match target package name against candidate stems.
    2. Match against embedded_name from -pkg.el candidates.
    3. Default to first candidate.
    """
    if init_file is None:
        return 0
    from soma_inits_upgrades.deps_resolution import determine_package_name

    target = determine_package_name(None, init_file)
    for i, c in enumerate(candidates):
        if c.stem == target:
            return i
    for i, c in enumerate(candidates):
        if c.embedded_name == target:
            return i
    return 0


def select_package_file(
    candidates: list[PackageCandidate],
    init_file: str | None, repo_url: str | None,
    input_fn: UserInputFn | None = None,
) -> PackageCandidate:
    """Prompt user to select a package when multiple candidates exist.

    Single-candidate lists auto-select without prompting.
    """
    if len(candidates) == 1:
        return candidates[0]
    resolved_fn = input_fn if input_fn is not None else default_input
    suggested = compute_suggested_index(candidates, init_file)
    if init_file is not None:
        eprint_prompt(f"While processing {init_file} multiple packages were found")
    if repo_url is not None:
        eprint_prompt(f"in {repo_url}:")
    for i, c in enumerate(candidates):
        tag = "  [suggested]" if i == suggested else ""
        eprint_prompt(f"  {i + 1}. {c.stem}{tag}")
    return _prompt_loop(candidates, resolved_fn, suggested)


def _prompt_loop(
    candidates: list[PackageCandidate],
    resolved_fn: UserInputFn, suggested: int,
) -> PackageCandidate:
    """Validation loop for user package selection."""
    prompt = f"Select the package to use (suggested: {suggested + 1}): "
    while True:
        try:
            choice = resolved_fn(prompt).strip()
        except EOFError:
            return candidates[suggested]
        if not choice:
            eprint_prompt("Please enter a number to select a package.")
            continue
        try:
            num = int(choice)
        except ValueError:
            eprint_error("Invalid choice")
            continue
        if 1 <= num <= len(candidates):
            return candidates[num - 1]
        eprint_error("Invalid choice")
