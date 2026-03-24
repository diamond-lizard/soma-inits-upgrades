"""Tests for summary.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.summary import (
    compile_security_summary,
    extract_risk_rating,
    group_entries_by_rating,
    write_security_summary_report,
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

