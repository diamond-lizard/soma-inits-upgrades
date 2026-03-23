"""Tests for prompts.py (helpers + security review prompt)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts import (
    format_common_header,
    format_malformed_context,
    generate_security_review_prompt,
)


def test_format_common_header_contains_key_fields() -> None:
    """Verify header includes all context fields and diff direction."""
    result = format_common_header("dash", "https://github.com/magnars/dash.el", "aaa", "bbb")
    assert "dash" in result
    assert "https://github.com/magnars/dash.el" in result
    assert "aaa" in result
    assert "bbb" in result
    assert "git diff aaa bbb" in result
    assert "OLD pinned version" in result
    assert "NEW latest version" in result


def test_format_malformed_context_returns_empty_when_none() -> None:
    """Verify empty string when malformed_path is None."""
    assert format_malformed_context(None, "reason", "fix") == ""


def test_format_malformed_context_returns_empty_when_missing(tmp_path: Path) -> None:
    """Verify empty string when malformed_path does not exist."""
    missing = tmp_path / "nonexistent.malformed"
    assert format_malformed_context(missing, "reason", "fix") == ""


def test_format_malformed_context_includes_content(tmp_path: Path) -> None:
    """Verify context section when malformed file exists."""
    malformed = tmp_path / "report.malformed"
    malformed.write_text("bad content", encoding="utf-8")
    result = format_malformed_context(malformed, "bad rating", "fix the rating")
    assert "Previous Attempt" in result
    assert str(malformed) in result
    assert "bad rating" in result
    assert "fix the rating" in result


def test_security_review_prompt_contains_key_phrases(tmp_path: Path) -> None:
    """Verify security review prompt includes all required elements."""
    diff = tmp_path / "test.diff"
    output = tmp_path / "review.md"
    result = generate_security_review_prompt(
        "dash", "https://github.com/magnars/dash.el", "aaa", "bbb", diff, output,
    )
    assert "Security Review" in result
    assert "shell-command" in result
    assert "call-process" in result
    assert "eval" in result
    assert "advice-add" in result
    assert "Obfuscated" in result
    assert "Risk Rating" in result
    assert str(diff) in result
    assert str(output) in result
    assert "dash" in result


def test_security_review_prompt_includes_malformed_context(tmp_path: Path) -> None:
    """Verify malformed context appears when malformed file exists."""
    diff = tmp_path / "test.diff"
    output = tmp_path / "review.md"
    malformed = tmp_path / "review.malformed"
    malformed.write_text("old bad review", encoding="utf-8")
    result = generate_security_review_prompt(
        "dash", "https://github.com/magnars/dash.el", "aaa", "bbb",
        diff, output, malformed_report_path=malformed,
    )
    assert "Previous Attempt" in result
    assert "Risk Rating line" in result
