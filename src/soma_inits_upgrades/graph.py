"""Dependency graph: build entries, inversion, validation."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

GraphDict = dict[str, dict[str, Any]]


def read_graph(path: Path) -> tuple[GraphDict, bool]:
    """Read the dependency graph JSON file.

    Returns (graph_dict, restored). If missing, returns ({}, False).
    On invalid JSON, attempts .bak restore. Returns ({}, True) if
    both main and backup are invalid/missing.
    """
    import json

    if not path.exists():
        return {}, False
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw), False
    except (json.JSONDecodeError, OSError):
        return _restore_from_backup(path)


def _restore_from_backup(path: Path) -> tuple[GraphDict, bool]:
    """Attempt to restore graph from .bak file."""
    import json
    import shutil

    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        print(f"Warning: corrupt graph at {path}, no backup", file=sys.stderr)
        return {}, True
    try:
        raw = bak.read_text(encoding="utf-8")
        graph = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        print(f"Warning: corrupt graph and backup at {path}", file=sys.stderr)
        return {}, True
    shutil.copy2(bak, path)
    print(f"Warning: restored graph from backup at {bak}", file=sys.stderr)
    return graph, True


def write_graph(path: Path, graph: GraphDict) -> None:
    """Write the dependency graph atomically with backup-on-write.

    Creates a .bak copy before writing, then writes via .tmp + rename.
    Raises OSError on write failure.
    """
    import json
    import shutil

    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
    content = json.dumps(graph, indent=2)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def add_entry(
    graph: GraphDict,
    init_file: str,
    package: str,
    min_emacs_version: str | None,
    depends_on: list[str],
) -> GraphDict:
    """Add or update an entry in the dependency graph."""
    graph[init_file] = {
        "package": package,
        "min_emacs_version": min_emacs_version,
        "depends_on": depends_on,
        "depended_on_by": [],
    }
    return graph


def remove_entries(graph: GraphDict, keys: list[str]) -> GraphDict:
    """Remove all specified keys from the graph in a single pass."""
    for key in keys:
        graph.pop(key, None)
    return graph


def build_package_to_key_map(graph: GraphDict) -> dict[str, str]:
    """Build mapping from package name to init file name (key)."""
    return {entry["package"]: key for key, entry in graph.items()}


def invert_dependencies(graph: GraphDict) -> GraphDict:
    """Populate depended_on_by from depends_on lists.

    Only includes packages that have entries in the graph.
    """
    pkg_map = build_package_to_key_map(graph)
    inverted: dict[str, list[str]] = {key: [] for key in graph}
    for _key, entry in graph.items():
        src_pkg = entry["package"]
        for dep_pkg in entry.get("depends_on", []):
            dep_key = pkg_map.get(dep_pkg)
            if dep_key is not None:
                inverted[dep_key].append(src_pkg)
    for key in graph:
        graph[key]["depended_on_by"] = sorted(set(inverted[key]))
    return graph


def check_duplicate_packages(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Check no two entries share the same package name."""
    seen: dict[str, list[str]] = {}
    for key, entry in graph.items():
        pkg = entry["package"]
        seen.setdefault(pkg, []).append(key)
    return [
        f"Duplicate package '{pkg}': {', '.join(keys)}"
        for pkg, keys in seen.items()
        if len(keys) > 1
    ]


def check_depended_on_by_entries(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Check all depended_on_by entries exist in the graph."""
    warnings: list[str] = []
    for key, entry in graph.items():
        for pkg in entry.get("depended_on_by", []):
            if pkg not in package_map:
                warnings.append(
                    f"{key}: depended_on_by '{pkg}' not in graph"
                )
    return warnings


def check_inverse_symmetry(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Check depends_on/depended_on_by are symmetric within graph."""
    warnings: list[str] = []
    for _key, entry in graph.items():
        src_pkg = entry["package"]
        for dep_pkg in entry.get("depends_on", []):
            dep_key = package_map.get(dep_pkg)
            if dep_key is None:
                continue
            dep_entry = graph[dep_key]
            if src_pkg not in dep_entry.get("depended_on_by", []):
                warnings.append(
                    f"{dep_pkg} missing {src_pkg} in depended_on_by"
                )
    return warnings


def check_circular_dependencies(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Detect circular dependencies via TopologicalSorter."""
    import graphlib

    sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter()
    for _key, entry in graph.items():
        pkg = entry["package"]
        in_graph_deps = [
            d for d in entry.get("depends_on", []) if d in package_map
        ]
        sorter.add(pkg, *in_graph_deps)
    try:
        sorter.prepare()
    except graphlib.CycleError as exc:
        return [f"Circular dependency detected: {exc.args[1]}"]
    return []


def validate_graph(graph: GraphDict) -> list[str]:
    """Run all validation checks, return combined warnings."""
    pkg_map = build_package_to_key_map(graph)
    warnings: list[str] = []
    warnings.extend(check_duplicate_packages(graph, pkg_map))
    warnings.extend(check_depended_on_by_entries(graph, pkg_map))
    warnings.extend(check_inverse_symmetry(graph, pkg_map))
    warnings.extend(check_circular_dependencies(graph, pkg_map))
    return warnings
