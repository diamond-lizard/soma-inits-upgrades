"""Tests for graph.py: entry ops, inversion, and validation."""

from __future__ import annotations

from soma_inits_upgrades.graph_entry import add_entry, remove_entries
from soma_inits_upgrades.graph_inversion import invert_dependencies
from soma_inits_upgrades.graph_validation import validate_graph


def _pkgs(
    name: str, ver: str | None = None, deps: list[str] | None = None,
) -> list[dict[str, object]]:
    """Build a single-element packages list for add_entry."""
    return [{"package": name, "repo_url": f"https://github.com/t/{name}",
             "min_emacs_version": ver, "depends_on": deps or []}]


def _two_entry_graph() -> dict:
    """Graph where magit depends on dash."""
    g: dict = {}
    add_entry(g, "soma-dash-init.el", _pkgs("dash", "26.1"))
    add_entry(g, "soma-magit-init.el", _pkgs("magit", "27.1", ["dash"]))
    return g


def test_add_entry_fields() -> None:
    """Verify add_entry sets all fields correctly."""
    g: dict = {}
    add_entry(g, "soma-dash-init.el", _pkgs("dash", "26.1", ["cl-lib"]))
    entry = g["soma-dash-init.el"]
    assert entry["packages"][0]["package"] == "dash"
    assert entry["packages"][0]["min_emacs_version"] == "26.1"
    assert entry["packages"][0]["depends_on"] == ["cl-lib"]
    assert entry["depended_on_by"] == []


def test_remove_existing_keys() -> None:
    """Verify removal of existing keys."""
    g = _two_entry_graph()
    remove_entries(g, ["soma-dash-init.el"])
    assert "soma-dash-init.el" not in g
    assert "soma-magit-init.el" in g


def test_remove_nonexistent_keys() -> None:
    """Verify non-existent keys are silently ignored."""
    g = _two_entry_graph()
    remove_entries(g, ["no-such-key.el"])
    assert len(g) == 2


def test_remove_empty_list() -> None:
    """Verify graph unchanged with empty key list."""
    g = _two_entry_graph()
    remove_entries(g, [])
    assert len(g) == 2


def test_validate_consistent() -> None:
    """A consistent graph produces no warnings."""
    g = _two_entry_graph()
    invert_dependencies(g)
    assert validate_graph(g) == []


def test_validate_broken_symmetry() -> None:
    """Missing depended_on_by triggers a warning."""
    g = _two_entry_graph()
    warnings = validate_graph(g)
    assert any("missing" in w for w in warnings)


def test_validate_duplicate_packages() -> None:
    """Two entries with same package name triggers a warning."""
    g: dict = {}
    add_entry(g, "soma-a-init.el", _pkgs("dash"))
    add_entry(g, "soma-b-init.el", _pkgs("dash"))
    warnings = validate_graph(g)
    assert any("Duplicate" in w for w in warnings)


def test_validate_cycle_detection() -> None:
    """Circular dependency is detected."""
    g: dict = {}
    add_entry(g, "soma-a-init.el", _pkgs("pkg-a", deps=["pkg-b"]))
    add_entry(g, "soma-b-init.el", _pkgs("pkg-b", deps=["pkg-a"]))
    warnings = validate_graph(g)
    assert any("Circular" in w for w in warnings)


def test_validate_no_cycle() -> None:
    """Linear dependencies produce no cycle warning."""
    g = _two_entry_graph()
    invert_dependencies(g)
    cycle_warnings = [w for w in validate_graph(g) if "Circular" in w]
    assert cycle_warnings == []
