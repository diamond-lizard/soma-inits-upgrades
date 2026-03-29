"""Entry artifact management: path resolution and deletion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.git_ops import safe_rmtree

if TYPE_CHECKING:
    from pathlib import Path


def get_entry_artifact_paths(
    init_file_name: str, output_dir: Path,
) -> dict[str, list[Path]]:
    """Return categorized artifact paths for an entry.

    Returns a dict with keys 'permanent', 'temp', and 'state'.
    """
    init_stem = init_file_name.removesuffix(".el")
    tmp_dir = output_dir / ".tmp" / init_stem
    state_dir = output_dir / ".state"

    permanent: list[Path] = [
        output_dir / f"{init_file_name}-security-review.md",
        output_dir / f"{init_file_name}-security-review.md.malformed",
        output_dir / f"{init_file_name}-upgrade-process.md",
        output_dir / f"{init_file_name}-upgrade-process.md.malformed",
        tmp_dir / f"{init_stem}-upgrade-analysis.json.malformed",
    ]

    temp: list[Path] = [tmp_dir]

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
        else:
            path.unlink(missing_ok=True)
