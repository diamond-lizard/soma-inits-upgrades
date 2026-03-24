"""Tests for graph.py."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.graph import (
    read_graph,
    write_graph,
)

if TYPE_CHECKING:
    from pathlib import Path


def _sample_graph() -> dict:
    """Return a sample graph with two entries."""
    return {
        "soma-dash-init.el": {
            "package": "dash",
            "min_emacs_version": "26.1",
            "depends_on": [],
            "depended_on_by": [],
        },
        "soma-magit-init.el": {
            "package": "magit",
            "min_emacs_version": "27.1",
            "depends_on": ["dash"],
            "depended_on_by": [],
        },
    }


def test_read_missing(tmp_path: Path) -> None:
    """Read returns empty dict and False when file missing."""
    graph, restored = read_graph(tmp_path / "graph.json")
    assert graph == {}
    assert restored is False


def test_read_valid(tmp_path: Path) -> None:
    """Read returns parsed dict when file is valid JSON."""
    path = tmp_path / "graph.json"
    data = _sample_graph()
    path.write_text(json.dumps(data), encoding="utf-8")
    graph, restored = read_graph(path)
    assert graph == data
    assert restored is False


def test_read_invalid_with_backup(tmp_path: Path) -> None:
    """Read restores from .bak when main file is corrupt."""
    path = tmp_path / "graph.json"
    bak = tmp_path / "graph.json.bak"
    path.write_text("not json", encoding="utf-8")
    data = _sample_graph()
    bak.write_text(json.dumps(data), encoding="utf-8")
    graph, restored = read_graph(path)
    assert graph == data
    assert restored is True
    assert json.loads(path.read_text(encoding="utf-8")) == data


def test_read_invalid_no_backup(tmp_path: Path) -> None:
    """Read returns empty dict and True when both are bad."""
    path = tmp_path / "graph.json"
    path.write_text("not json", encoding="utf-8")
    graph, restored = read_graph(path)
    assert graph == {}
    assert restored is True


def test_write_creates_backup(tmp_path: Path) -> None:
    """Write creates a .bak before overwriting."""
    path = tmp_path / "graph.json"
    original = {"old": {"package": "old", "depends_on": []}}
    path.write_text(json.dumps(original), encoding="utf-8")
    write_graph(path, _sample_graph())
    bak = tmp_path / "graph.json.bak"
    assert bak.exists()
    assert json.loads(bak.read_text(encoding="utf-8")) == original


def test_write_atomic(tmp_path: Path) -> None:
    """Write produces valid JSON and no leftover .tmp."""
    path = tmp_path / "graph.json"
    write_graph(path, _sample_graph())
    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
    assert json.loads(path.read_text(encoding="utf-8")) == _sample_graph()
