"""Tests for output_validation.py: file checks, content validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.output_validation import (
    validate_security_review_content,
    validate_upgrade_analysis_output,
)
from soma_inits_upgrades.output_validation_tasks import (
    validate_upgrade_report_content,
)

if TYPE_CHECKING:
    from pathlib import Path


def _noop_heal(path: Path, task: str, ctx: object) -> bool:
    """No-op self-heal stub that records calls."""
    return False


class HealRecorder:
    """Records self-healing calls."""

    def __init__(self) -> None:
        """Initialize with empty call list."""
        self.calls: list[tuple[str, str]] = []

    def __call__(self, path: Path, task: str, ctx: object) -> bool:
        """Record the call and return False."""
        self.calls.append((str(path), task))
        return False


def test_security_review_valid(tmp_path: Path) -> None:
    """Valid security review with risk rating passes."""
    f = tmp_path / "review.md"
    f.write_text("# Review\nRisk Rating: low\n", encoding="utf-8")
    assert validate_security_review_content(f, _noop_heal, None) is True  # type: ignore[arg-type]


def test_security_review_invalid(tmp_path: Path) -> None:
    """Missing risk rating renames to .malformed."""
    f = tmp_path / "review.md"
    f.write_text("# Review\nNo rating here.\n", encoding="utf-8")
    heal = HealRecorder()
    assert validate_security_review_content(f, heal, None) is False  # type: ignore[arg-type]
    assert (tmp_path / "review.md.malformed").exists()


def test_upgrade_analysis_valid_json(tmp_path: Path) -> None:
    """Valid JSON passes validation."""
    f = tmp_path / "analysis.json"
    f.write_text('{"change_summary": "ok"}', encoding="utf-8")
    assert validate_upgrade_analysis_output(f, _noop_heal, None) is True  # type: ignore[arg-type]


def test_upgrade_analysis_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON renames to .malformed."""
    f = tmp_path / "analysis.json"
    f.write_text('{"broken":', encoding="utf-8")
    heal = HealRecorder()
    assert validate_upgrade_analysis_output(f, heal, None) is False  # type: ignore[arg-type]
    assert (tmp_path / "analysis.json.malformed").exists()


def test_upgrade_analysis_strips_fences(tmp_path: Path) -> None:
    """Code fences are stripped and cleaned content written back."""
    f = tmp_path / "analysis.json"
    f.write_text('```json\n{"change_summary": "ok"}\n```\n', encoding="utf-8")
    assert validate_upgrade_analysis_output(f, _noop_heal, None) is True  # type: ignore[arg-type]
    assert not f.read_text(encoding="utf-8").startswith("```")


def test_upgrade_report_valid(tmp_path: Path) -> None:
    """Report with enough sections passes."""
    f = tmp_path / "report.md"
    f.write_text("# Summary of Changes\n## Breaking Changes\n", encoding="utf-8")
    assert validate_upgrade_report_content(f, _noop_heal, None) is True  # type: ignore[arg-type]


def test_upgrade_report_invalid(tmp_path: Path) -> None:
    """Report lacking sections renames to .malformed."""
    f = tmp_path / "report.md"
    f.write_text("# Just some text\n", encoding="utf-8")
    heal = HealRecorder()
    assert validate_upgrade_report_content(f, heal, None) is False  # type: ignore[arg-type]
    assert (tmp_path / "report.md.malformed").exists()

