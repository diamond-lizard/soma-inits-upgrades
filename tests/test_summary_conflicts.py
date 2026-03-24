"""Tests for summary_conflicts.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.summary_conflicts import (
    format_version_conflicts_report,
    identify_version_conflicts,
    write_version_conflicts,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_identify_version_conflicts_found() -> None:
    """Identifies packages requiring newer Emacs."""
    graph = {
        "a.el": {
            "package": "pkg-a",
            "min_emacs_version": "30.1",
        },
        "b.el": {
            "package": "pkg-b",
            "min_emacs_version": "27.1",
        },
    }
    result = identify_version_conflicts(graph, ["a.el", "b.el"], "28.1")
    assert len(result) == 1
    assert result[0]["package"] == "pkg-a"
    assert result[0]["min_emacs_version"] == "30.1"


def test_identify_version_conflicts_none() -> None:
    """Returns empty list when no conflicts."""
    graph = {
        "a.el": {
            "package": "pkg-a",
            "min_emacs_version": "27.1",
        },
    }
    result = identify_version_conflicts(graph, ["a.el"], "29.1")
    assert result == []


def test_identify_version_conflicts_missing_entry() -> None:
    """Skips entries not in graph."""
    result = identify_version_conflicts({}, ["a.el"], "28.1")
    assert result == []


def test_identify_version_conflicts_no_min_version() -> None:
    """Skips entries with no min_emacs_version."""
    graph = {"a.el": {"package": "pkg-a", "min_emacs_version": None}}
    result = identify_version_conflicts(graph, ["a.el"], "28.1")
    assert result == []


def test_format_version_conflicts_report_empty() -> None:
    """Returns empty string for no conflicts."""
    assert format_version_conflicts_report([], "28.1") == ""


def test_format_version_conflicts_report_content() -> None:
    """Formats conflicts into markdown."""
    conflicts = [
        {
            "package": "pkg-a",
            "min_emacs_version": "30.1",
            "user_version": "28.1",
        },
    ]
    result = format_version_conflicts_report(conflicts, "28.1")
    assert "# Emacs Version Conflicts" in result
    assert "**pkg-a**" in result
    assert "30.1" in result


def test_write_version_conflicts_creates_file(tmp_path: Path) -> None:
    """Writes conflict report when conflicts exist."""
    graph = {
        "a.el": {"package": "pkg-a", "min_emacs_version": "30.1"},
    }
    out = tmp_path / "conflicts.md"
    write_version_conflicts(graph, ["a.el"], "28.1", out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "pkg-a" in text


def test_write_version_conflicts_no_file(tmp_path: Path) -> None:
    """Does not create file when no conflicts."""
    graph = {
        "a.el": {"package": "pkg-a", "min_emacs_version": "27.1"},
    }
    out = tmp_path / "conflicts.md"
    write_version_conflicts(graph, ["a.el"], "29.1", out)
    assert not out.exists()
