"""Tests for multi-package graph entries: structure and mapping."""

from __future__ import annotations

from soma_inits_upgrades.graph_entry import add_entry, build_package_to_key_map
from soma_inits_upgrades.graph_inversion import invert_dependencies


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


def test_single_package_entry() -> None:
    """Single-package entry produces expected structure."""
    g: dict = {}
    add_entry(g, "soma-dash-init.el", [_pkg("dash", "26.1")])
    entry = g["soma-dash-init.el"]
    assert len(entry["packages"]) == 1
    assert entry["packages"][0]["package"] == "dash"
    assert entry["depended_on_by"] == []


def test_two_package_entry() -> None:
    """Two packages in one init file are stored in packages list."""
    g: dict = {}
    pkgs = [_pkg("outshine"), _pkg("outorg")]
    add_entry(g, "soma-outshine-and-outorg-init.el", pkgs)
    entry = g["soma-outshine-and-outorg-init.el"]
    assert len(entry["packages"]) == 2
    names = [p["package"] for p in entry["packages"]]
    assert "outshine" in names
    assert "outorg" in names


def test_package_to_key_map_both_packages() -> None:
    """build_package_to_key_map maps both packages to same key."""
    g: dict = {}
    pkgs = [_pkg("outshine"), _pkg("outorg")]
    add_entry(g, "soma-outshine-and-outorg-init.el", pkgs)
    pkg_map = build_package_to_key_map(g)
    assert pkg_map["outshine"] == "soma-outshine-and-outorg-init.el"
    assert pkg_map["outorg"] == "soma-outshine-and-outorg-init.el"


def test_intra_init_file_deps_filtered() -> None:
    """Intra-init-file deps excluded from depended_on_by."""
    g: dict = {}
    pkgs = [
        _pkg("outshine", deps=["outorg"]),
        _pkg("outorg"),
    ]
    add_entry(g, "soma-outshine-and-outorg-init.el", pkgs)
    invert_dependencies(g)
    entry = g["soma-outshine-and-outorg-init.el"]
    assert entry["depended_on_by"] == []


def test_cross_init_file_deps_recorded() -> None:
    """Cross-init-file deps recorded as init-file keys."""
    g: dict = {}
    add_entry(g, "soma-dash-init.el", [_pkg("dash")])
    add_entry(g, "soma-magit-init.el", [_pkg("magit", deps=["dash"])])
    invert_dependencies(g)
    assert g["soma-dash-init.el"]["depended_on_by"] == [
        "soma-magit-init.el",
    ]
    assert g["soma-magit-init.el"]["depended_on_by"] == []
