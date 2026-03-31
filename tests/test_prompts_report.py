"""Tests for prompts_report.py (upgrade report prompt builder)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts_helpers import (
    format_dependency_context,
    shorten_home_in_text,
)
from soma_inits_upgrades.prompts_report import generate_upgrade_report_prompt


def test_upgrade_report_prompt_key_phrases(tmp_path: Path) -> None:
    """Verify upgrade report prompt includes required sections."""
    analysis = tmp_path / "analysis.json"
    output = tmp_path / "report.md"
    dep_ctx = format_dependency_context(["s"], "28.1", True, "27.2")
    result = generate_upgrade_report_prompt(
        [{"package_name": "dash",
          "repo_url": "https://github.com/magnars/dash.el",
          "pinned_ref": "aaa", "latest_ref": "bbb"}],
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
    assert shorten_home_in_text(str(analysis)) in result
    assert shorten_home_in_text(str(output)) in result
    assert "NO code snippets" in result


def test_upgrade_report_prompt_malformed(tmp_path: Path) -> None:
    """Verify malformed context in upgrade report prompt."""
    analysis = tmp_path / "analysis.json"
    output = tmp_path / "report.md"
    malformed = tmp_path / "report.malformed"
    malformed.write_text("bad report", encoding="utf-8")
    result = generate_upgrade_report_prompt(
        [{"package_name": "dash",
          "repo_url": "https://github.com/magnars/dash.el",
          "pinned_ref": "aaa", "latest_ref": "bbb"}],
        analysis, output, "", malformed_report_path=malformed,
    )
    assert "Previous Attempt" in result
    assert "required report sections" in result


def test_upgrade_report_two_repos(tmp_path: Path) -> None:
    """Two-repo upgrade report references multi-repo data."""
    analysis = tmp_path / "analysis.json"
    output = tmp_path / "report.md"
    result = generate_upgrade_report_prompt(
        [{"package_name": "outshine",
          "repo_url": "https://github.com/alphapapa/outshine",
          "pinned_ref": "aaa", "latest_ref": "bbb"},
         {"package_name": "outorg",
          "repo_url": "https://github.com/alphapapa/outorg",
          "pinned_ref": "ccc", "latest_ref": "ddd"}],
        analysis, output, "",
    )
    assert "outshine" in result
    assert "outorg" in result
    assert shorten_home_in_text(str(analysis)) in result
    assert "Upgrade Report" in result


def test_upgrade_report_prompt_includes_preamble(tmp_path: Path) -> None:
    """Verify the upgrade report prompt starts with the preamble."""
    analysis = tmp_path / "analysis.json"
    output = tmp_path / "report.md"
    result = generate_upgrade_report_prompt(
        [{"package_name": "dash", "repo_url": "https://github.com/magnars/dash.el",
          "pinned_ref": "aaa", "latest_ref": "bbb"}],
        analysis, output, "",
    )
    assert result.startswith("You will be given the task")
    assert "elpaca" in result
