"""Package candidate selection for monorepo disambiguation."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


def _default_input(prompt: str) -> str:
    """Thin wrapper around input() for DI default."""
    return input(prompt)


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
    resolved_fn = input_fn if input_fn is not None else _default_input
    suggested = compute_suggested_index(candidates, init_file)
    if init_file is not None:
        print(f"While processing {init_file} multiple packages were found", file=sys.stderr)
    if repo_url is not None:
        print(f"in {repo_url}:", file=sys.stderr)
    for i, c in enumerate(candidates):
        tag = "  [suggested]" if i == suggested else ""
        print(f"  {i + 1}. {c.stem}{tag}", file=sys.stderr)
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
            print("Please enter a number to select a package.", file=sys.stderr)
            continue
        try:
            num = int(choice)
        except ValueError:
            print("Invalid choice", file=sys.stderr)
            continue
        if 1 <= num <= len(candidates):
            return candidates[num - 1]
        print("Invalid choice", file=sys.stderr)
