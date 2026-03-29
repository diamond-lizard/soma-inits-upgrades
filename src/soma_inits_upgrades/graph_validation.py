"""Dependency graph: validation checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.graph_entry import build_package_to_key_map

if TYPE_CHECKING:
    from soma_inits_upgrades.graph import GraphDict


def check_duplicate_packages(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Check no two init-file entries share the same package name."""
    seen: dict[str, list[str]] = {}
    for key, entry in graph.items():
        for pkg in entry.get("packages", []):
            seen.setdefault(pkg["package"], []).append(key)
    return [
        f"Duplicate package '{pkg}': {', '.join(keys)}"
        for pkg, keys in seen.items()
        if len(keys) > 1
    ]


def check_depended_on_by_entries(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Check all depended_on_by entries exist in the graph.

    depended_on_by contains init-file keys, so look up in graph.
    """
    return [
        f"{key}: depended_on_by '{dep_key}' not in graph"
        for key, entry in graph.items()
        for dep_key in entry.get("depended_on_by", [])
        if dep_key not in graph
    ]

def check_inverse_symmetry(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Check depends_on/depended_on_by are symmetric within graph.

    depends_on contains package names; depended_on_by contains
    init-file keys.  Bridge via package_map.  Intra-init-file
    deps are intentionally absent from depended_on_by.
    """
    warnings: list[str] = []
    for src_key, entry in graph.items():
        for pkg in entry.get("packages", []):
            for dep_pkg in pkg.get("depends_on", []):
                dep_key = package_map.get(dep_pkg)
                if dep_key is None or dep_key == src_key:
                    continue
                dep_entry = graph[dep_key]
                if src_key not in dep_entry.get("depended_on_by", []):
                    warnings.append(
                        f"{dep_pkg} missing {src_key} in depended_on_by"
                    )
    return warnings


def check_circular_dependencies(
    graph: GraphDict, package_map: dict[str, str],
) -> list[str]:
    """Detect circular dependencies at init-file level."""
    import graphlib

    sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter()
    for key, entry in graph.items():
        dep_keys: set[str] = set()
        for pkg in entry.get("packages", []):
            for dep_pkg in pkg.get("depends_on", []):
                dep_key = package_map.get(dep_pkg)
                if dep_key is not None and dep_key != key:
                    dep_keys.add(dep_key)
        sorter.add(key, *dep_keys)
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
