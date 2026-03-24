"""Tests for summary.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.summary import (
    compile_security_summary,
    extract_risk_rating,
    format_version_conflicts_report,
    group_entries_by_rating,
    identify_version_conflicts,
    write_security_summary_report,
    write_version_conflicts,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_review(tmp_path: Path, name: str, rating: str) -> None:
    """Write a fake security review file with a given rating."""
    path = tmp_path / f"{name}-security-review.md"
    path.write_text(
        f"# Review\n\nRisk Rating: {rating}\n", encoding="utf-8",
    )


def test_extract_rating_missing_file(tmp_path: Path) -> None:
    """Returns None when file does not exist."""
    result = extract_risk_rating(tmp_path / "nonexistent.md")
    assert result is None


def test_extract_rating_valid(tmp_path: Path) -> None:
    """Returns lowercase rating for valid file."""
    _write_review(tmp_path, "pkg", "High")
    result = extract_risk_rating(tmp_path / "pkg-security-review.md")
    assert result == "high"


def test_extract_rating_unknown(tmp_path: Path) -> None:
    """Returns 'unknown' when file has no rating line."""
    path = tmp_path / "bad.md"
    path.write_text("No rating here\n", encoding="utf-8")
    assert extract_risk_rating(path) == "unknown"


def test_extract_rating_invalid_value(tmp_path: Path) -> None:
    """Returns 'unknown' for unrecognized rating value."""
    path = tmp_path / "odd.md"
    path.write_text("Risk Rating: extreme\n", encoding="utf-8")
    assert extract_risk_rating(path) == "unknown"


def test_group_entries_by_rating() -> None:
    """Groups entries correctly by rating."""
    entries = [("a.el", "high"), ("b.el", "low"), ("c.el", "high")]
    result = group_entries_by_rating(entries)
    assert result == {"high": ["a.el", "c.el"], "low": ["b.el"]}


def test_group_entries_empty() -> None:
    """Returns empty dict for empty input."""
    assert group_entries_by_rating([]) == {}


def test_compile_security_summary(tmp_path: Path) -> None:
    """Compiles ratings, skipping entries with no review file."""
    _write_review(tmp_path, "a.el", "high")
    _write_review(tmp_path, "c.el", "low")
    names = ["a.el", "b.el", "c.el"]
    result = compile_security_summary(names, tmp_path)
    assert result == {"high": ["a.el"], "low": ["c.el"]}


def test_write_security_summary_report(tmp_path: Path) -> None:
    """Writes markdown with headings in severity order."""
    grouped = {"low": ["pkg-a.el"], "high": ["pkg-b.el", "pkg-c.el"]}
    out = tmp_path / "summary.md"
    write_security_summary_report(grouped, out)
    text = out.read_text(encoding="utf-8")
    assert "## High" in text
    assert "## Low" in text
    high_pos = text.index("## High")
    low_pos = text.index("## Low")
    assert high_pos < low_pos


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
