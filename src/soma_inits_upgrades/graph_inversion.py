"""Dependency graph: dependency inversion (depended_on_by)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.graph_entry import build_package_to_key_map

if TYPE_CHECKING:
    from soma_inits_upgrades.graph import GraphDict


def invert_dependencies(graph: GraphDict) -> GraphDict:
    """Populate depended_on_by from depends_on lists.

    depended_on_by contains init-file keys (not package names).
    Intra-init-file dependencies are filtered out.
    """
    pkg_map = build_package_to_key_map(graph)
    inverted: dict[str, set[str]] = {key: set() for key in graph}
    for src_key, entry in graph.items():
        for pkg in entry.get("packages", []):
            for dep_pkg in pkg.get("depends_on", []):
                dep_key = pkg_map.get(dep_pkg)
                if dep_key is not None and dep_key != src_key:
                    inverted[dep_key].add(src_key)
    for key in graph:
        graph[key]["depended_on_by"] = sorted(inverted[key])
    return graph
