"""Dependency graph: entry operations and package mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from soma_inits_upgrades.graph import GraphDict


def add_entry(
    graph: GraphDict,
    init_file: str,
    packages: list[dict[str, Any]],
) -> GraphDict:
    """Add or update an entry in the dependency graph.

    Each element in packages has keys: package, repo_url,
    depends_on (list[str]), min_emacs_version (str | None).
    """
    graph[init_file] = {
        "packages": packages,
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
    return {
        pkg["package"]: key
        for key, entry in graph.items()
        for pkg in entry.get("packages", [])
    }
