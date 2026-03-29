"""Integration: two-repo graph entry structure and dependency filtering."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.graph_entry import add_entry
from soma_inits_upgrades.graph_inversion import invert_dependencies
from soma_inits_upgrades.graph_validation import validate_graph

if TYPE_CHECKING:
    from pathlib import Path

_INIT = "soma-outshine-and-outorg-init.el"
_URL_A = "https://github.com/emacs-packages/outshine"
_URL_B = "https://github.com/emacs-packages/outorg"


def _two_repo_graph() -> dict:
    """Build a graph with one multi-package init file entry."""
    g: dict = {}
    add_entry(g, _INIT, [
        {"package": "outshine", "repo_url": _URL_A,
         "depends_on": ["outorg"], "min_emacs_version": "26.1"},
        {"package": "outorg", "repo_url": _URL_B,
         "depends_on": [], "min_emacs_version": "25.1"},
    ])
    return g


def test_packages_list_has_two_elements() -> None:
    """Graph entry for two-repo init file has packages list of length 2."""
    g = _two_repo_graph()
    entry = g[_INIT]
    assert len(entry["packages"]) == 2
    names = {p["package"] for p in entry["packages"]}
    assert names == {"outshine", "outorg"}


def test_package_fields_correct() -> None:
    """Each package element has correct repo_url, depends_on, min_emacs."""
    g = _two_repo_graph()
    pkgs = {p["package"]: p for p in g[_INIT]["packages"]}
    assert pkgs["outshine"]["repo_url"] == _URL_A
    assert pkgs["outshine"]["depends_on"] == ["outorg"]
    assert pkgs["outshine"]["min_emacs_version"] == "26.1"
    assert pkgs["outorg"]["repo_url"] == _URL_B
    assert pkgs["outorg"]["depends_on"] == []
    assert pkgs["outorg"]["min_emacs_version"] == "25.1"


def test_intra_init_deps_filtered_from_depended_on_by() -> None:
    """Intra-init-file dependency does not appear in depended_on_by."""
    g = _two_repo_graph()
    invert_dependencies(g)
    assert _INIT not in g[_INIT].get("depended_on_by", [])


def test_cross_init_deps_appear_in_depended_on_by() -> None:
    """Cross-init-file dependency appears in depended_on_by."""
    g = _two_repo_graph()
    add_entry(g, "soma-magit-init.el", [
        {"package": "magit", "repo_url": "https://github.com/t/magit",
         "depends_on": ["outshine"], "min_emacs_version": "27.1"},
    ])
    invert_dependencies(g)
    assert "soma-magit-init.el" in g[_INIT]["depended_on_by"]
    assert _INIT not in g[_INIT]["depended_on_by"]


def test_graph_validates_cleanly() -> None:
    """Two-repo graph with inversion produces no warnings."""
    g = _two_repo_graph()
    invert_dependencies(g)
    assert validate_graph(g) == []


def test_graph_round_trips_via_json(tmp_path: Path) -> None:
    """Graph survives write/read cycle preserving packages list."""
    g = _two_repo_graph()
    path = tmp_path / "graph.json"
    write_graph(path, g)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert len(loaded[_INIT]["packages"]) == 2
