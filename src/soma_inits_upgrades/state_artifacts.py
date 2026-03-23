"""Entry artifact management: path resolution, deletion, state creation/reset/change detection."""

from __future__ import annotations

import sys
import sys


from soma_inits_upgrades.state import (
    atomic_write_json, detect_entry_field_changes, read_entry_state,
)
from soma_inits_upgrades.state_schema import EntryState
from soma_inits_upgrades.git_ops import safe_rmtree
from soma_inits_upgrades.state_schema import EntryState

def get_entry_artifact_paths(
    init_file_name: str, output_dir: Path,
) -> dict[str, list[Path]]:
    """Return categorized artifact paths for an entry.

    Returns a dict with keys 'permanent', 'temp', and 'state'.
    """
    init_stem = init_file_name.removesuffix(".el")
    tmp_dir = output_dir / ".tmp"
    state_dir = output_dir / ".state"

    permanent: list[Path] = [
        output_dir / f"{init_file_name}-security-review.md",
        output_dir / f"{init_file_name}-security-review.md.malformed",
        output_dir / f"{init_file_name}-upgrade-process.md",
        output_dir / f"{init_file_name}-upgrade-process.md.malformed",
        tmp_dir / f"{init_stem}-upgrade-analysis.json.malformed",
    ]

    temp: list[Path] = [
        tmp_dir / f"{init_stem}.diff",
        tmp_dir / f"{init_stem}-usage-analysis.json",
        tmp_dir / f"{init_stem}-upgrade-analysis.json",
        tmp_dir / f"{init_stem}-security-review.prompt.md",
        tmp_dir / f"{init_stem}-upgrade-analysis.prompt.md",
        tmp_dir / f"{init_stem}-upgrade-report.prompt.md",
        tmp_dir / init_stem,
    ]

    state: list[Path] = [state_dir / f"{init_file_name}.json"]

    return {"permanent": permanent, "temp": temp, "state": state}



def _collect_paths_to_delete(
    paths: dict[str, list[Path]],
    include_state: bool, include_permanent: bool, include_temp: bool,
) -> list[Path]:
    """Flatten selected path categories into a single list."""
    result: list[Path] = []
    if include_permanent:
        result.extend(paths["permanent"])
    if include_temp:
        result.extend(paths["temp"])
    if include_state:
        result.extend(paths["state"])
    return result


def delete_entry_artifacts(
    init_file_name: str,
    output_dir: Path,
    include_state: bool = False,
    include_permanent: bool = True,
    include_temp: bool = True,
) -> None:
    """Delete artifact files for an entry based on category flags."""
    paths = get_entry_artifact_paths(init_file_name, output_dir)
    targets = _collect_paths_to_delete(paths, include_state, include_permanent, include_temp)
    for path in targets:
        if path.is_dir():
            safe_rmtree(path, output_dir)


def reset_entry_state_if_modified(
    entry_dict: dict[str, str], state_dir: Path, output_dir: Path,
) -> bool:
    """Reset entry state if repo_url or pinned_ref changed.

    Returns True if the entry was modified and reset, False otherwise.
    """
    path = state_dir / f"{entry_dict['init_file']}.json"
    existing = read_entry_state(path)
    if existing is None:
        return False
    changed = detect_entry_field_changes(existing, entry_dict)
    if not changed:
        return False
    fields = ", ".join(changed)
    print(f"Warning: {entry_dict['init_file']} changed ({fields}), resetting", file=sys.stderr)
    delete_entry_artifacts(entry_dict["init_file"], output_dir)
    new_state = EntryState(
        init_file=entry_dict["init_file"],
        repo_url=entry_dict["repo_url"],
        pinned_ref=entry_dict["pinned_ref"],
    )
    atomic_write_json(path, new_state)
    return True
