"""Tests for prompts_upgrade.py and prompts_report.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts_report import generate_upgrade_report_prompt
from soma_inits_upgrades.prompts_upgrade import (
    format_dependency_context,
    generate_upgrade_analysis_prompt,
)


def test_format_dependency_context() -> None:
    """Verify dependency context formatting with and without deps."""
    with_deps = format_dependency_context(
        ["s", "ht"], "28.1", emacs_upgrade_required=True, emacs_version="27.2",
    )
    assert "s, ht" in with_deps
    assert "28.1" in with_deps
    assert "WARNING" in with_deps
    no_deps = format_dependency_context(
        [], None, emacs_upgrade_required=False, emacs_version="29.1",
    )
    assert "none" in no_deps
    assert "29.1" in no_deps
    assert "WARNING" not in no_deps


def test_upgrade_analysis_prompt_key_phrases(tmp_path: Path) -> None:
    """Verify upgrade analysis prompt includes required elements."""
    diff = tmp_path / "test.diff"
    usage = tmp_path / "usage.json"
    output = tmp_path / "analysis.json"
    dep_ctx = format_dependency_context(["s"], None, False, "29.1")
    result = generate_upgrade_analysis_prompt(
        "dash", "https://github.com/magnars/dash.el", "aaa", "bbb",
        diff, usage, output, dep_ctx,
    )
    assert "Upgrade Analysis" in result
    assert str(diff) in result
    assert str(usage) in result
    assert str(output) in result
    assert "schema" in result.lower()
    assert "breaking_api_changes" in result
    assert "dash" in result


def test_upgrade_analysis_prompt_malformed(tmp_path: Path) -> None:
    """Verify malformed context in upgrade analysis prompt."""
    diff = tmp_path / "test.diff"
    usage = tmp_path / "usage.json"
    output = tmp_path / "analysis.json"
    malformed = tmp_path / "analysis.malformed"
    malformed.write_text("bad json", encoding="utf-8")
    result = generate_upgrade_analysis_prompt(
        "dash", "https://github.com/magnars/dash.el", "aaa", "bbb",
        diff, usage, output, "", malformed_analysis_path=malformed,
    )
    assert "Previous Attempt" in result
    assert "not valid JSON" in result

def test_upgrade_report_prompt_key_phrases(tmp_path: Path) -> None:
    """Verify upgrade report prompt includes required sections."""
    analysis = tmp_path / "analysis.json"
    output = tmp_path / "report.md"
    dep_ctx = format_dependency_context(["s"], "28.1", True, "27.2")
    result = generate_upgrade_report_prompt(
        "dash", "https://github.com/magnars/dash.el", "aaa", "bbb",
        analysis, output, dep_ctx,
    )
    assert "Upgrade Report" in result
    assert "Summary of Changes" in result
    assert "Breaking Changes" in result
    assert "New Dependencies" in result
    assert "Removed or Changed Public API" in result
    assert "Configuration Impact Analysis" in result
    assert "Emacs Version Requirement" in result
    assert "Recommended Upgrade Approach" in result
    assert str(analysis) in result
    assert str(output) in result
    assert "NO code snippets" in result

def test_upgrade_report_prompt_malformed(tmp_path: Path) -> None:
    """Verify malformed context in upgrade report prompt."""
    analysis = tmp_path / "analysis.json"
    output = tmp_path / "report.md"
    malformed = tmp_path / "report.malformed"
    malformed.write_text("bad report", encoding="utf-8")
    result = generate_upgrade_report_prompt(
        "dash", "https://github.com/magnars/dash.el", "aaa", "bbb",
        analysis, output, "", malformed_report_path=malformed,
    )
    assert "Previous Attempt" in result
    assert "required report sections" in result
