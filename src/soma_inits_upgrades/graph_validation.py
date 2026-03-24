"""Dependency graph: inversion and validation."""

from __future__ import annotations

from soma_inits_upgrades.graph import GraphDict, build_package_to_key_map


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
    return [
        f"{key}: depended_on_by '{pkg}' not in graph"
        for key, entry in graph.items()
        for pkg in entry.get("depended_on_by", [])
        if pkg not in package_map
    ]

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
