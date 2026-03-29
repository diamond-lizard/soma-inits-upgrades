"""Tests for multi-package graph validation and cycle detection."""

from __future__ import annotations

from soma_inits_upgrades.graph_entry import add_entry
from soma_inits_upgrades.graph_inversion import invert_dependencies
from soma_inits_upgrades.graph_validation import validate_graph


def _pkg(
    name: str, ver: str | None = None, deps: list[str] | None = None,
) -> dict[str, object]:
    """Build a single package dict."""
    return {
        "package": name,
        "repo_url": f"https://github.com/t/{name}",
        "min_emacs_version": ver,
        "depends_on": deps or [],
    }


def test_depended_on_by_deduplication() -> None:
    """Multiple packages depending on same target deduplicated."""
    g: dict = {}
    add_entry(g, "soma-dash-init.el", [_pkg("dash")])
    pkgs = [_pkg("pkg-a", deps=["dash"]), _pkg("pkg-b", deps=["dash"])]
    add_entry(g, "soma-multi-init.el", pkgs)
    invert_dependencies(g)
    assert g["soma-dash-init.el"]["depended_on_by"] == [
        "soma-multi-init.el",
    ]


def test_cycle_detection_init_file_level() -> None:
    """Cycle detection operates at init-file level."""
    g: dict = {}
    add_entry(g, "a.el", [_pkg("pkg-a", deps=["pkg-b"])])
    add_entry(g, "b.el", [_pkg("pkg-b", deps=["pkg-a"])])
    warnings = validate_graph(g)
    assert any("Circular" in w for w in warnings)


def test_no_cycle_intra_init_file() -> None:
    """Intra-init-file dependency does not create a cycle."""
    g: dict = {}
    pkgs = [_pkg("outshine", deps=["outorg"]), _pkg("outorg")]
    add_entry(g, "soma-outshine-and-outorg-init.el", pkgs)
    invert_dependencies(g)
    cycle_warnings = [w for w in validate_graph(g) if "Circular" in w]
    assert cycle_warnings == []
