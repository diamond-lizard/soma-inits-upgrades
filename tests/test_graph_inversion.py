"""Tests for graph inversion (depended_on_by computation)."""

from __future__ import annotations

from soma_inits_upgrades.graph_entry import add_entry
from soma_inits_upgrades.graph_inversion import invert_dependencies


def _pkgs(
    name: str, ver: str | None = None, deps: list[str] | None = None,
) -> list[dict[str, object]]:
    """Build a single-element packages list for add_entry."""
    return [{"package": name, "repo_url": f"https://github.com/t/{name}",
             "min_emacs_version": ver, "depends_on": deps or []}]


def test_inversion() -> None:
    """Verify depended_on_by is computed from depends_on."""
    g: dict = {}
    add_entry(g, "soma-dash-init.el", _pkgs("dash", "26.1"))
    add_entry(g, "soma-magit-init.el", _pkgs("magit", "27.1", ["dash"]))
    invert_dependencies(g)
    assert g["soma-dash-init.el"]["depended_on_by"] == [
        "soma-magit-init.el",
    ]
    assert g["soma-magit-init.el"]["depended_on_by"] == []
