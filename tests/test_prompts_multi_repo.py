"""Tests for multi-repo prompt generation (Phase 1000)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts import generate_security_review_prompt
from soma_inits_upgrades.prompts_upgrade import (
    generate_upgrade_analysis_prompt,
)


def test_security_review_single_repo_equivalent(tmp_path: Path) -> None:
    """Single-repo security review prompt is functionally equivalent."""
    diff = tmp_path / "test.diff"
    output = tmp_path / "review.md"
    result = generate_security_review_prompt(
        [{"package_name": "dash",
          "repo_url": "https://github.com/magnars/dash.el",
          "pinned_ref": "aaa", "latest_ref": "bbb",
          "diff_path": diff}],
        output,
    )
    assert "dash" in result
    assert "https://github.com/magnars/dash.el" in result
    assert "aaa" in result
    assert "bbb" in result
    assert str(diff) in result
    assert "Security Review" in result
    assert "Risk Rating" in result


def test_security_review_two_repos(tmp_path: Path) -> None:
    """Two-repo security review lists both diff paths per repo."""
    diff1 = tmp_path / "outshine.diff"
    diff2 = tmp_path / "outorg.diff"
    output = tmp_path / "review.md"
    result = generate_security_review_prompt(
        [{"package_name": "outshine",
          "repo_url": "https://github.com/alphapapa/outshine",
          "pinned_ref": "aaa", "latest_ref": "bbb",
          "diff_path": diff1},
         {"package_name": "outorg",
          "repo_url": "https://github.com/alphapapa/outorg",
          "pinned_ref": "ccc", "latest_ref": "ddd",
          "diff_path": diff2}],
        output,
    )
    assert "outshine" in result
    assert "outorg" in result
    assert str(diff1) in result
    assert str(diff2) in result
    assert "https://github.com/alphapapa/outshine" in result
    assert "https://github.com/alphapapa/outorg" in result


def test_upgrade_analysis_two_repos(tmp_path: Path) -> None:
    """Two-repo upgrade analysis lists both analysis file paths."""
    diff1 = tmp_path / "outshine.diff"
    diff2 = tmp_path / "outorg.diff"
    usage1 = tmp_path / "outshine-usage.json"
    usage2 = tmp_path / "outorg-usage.json"
    output = tmp_path / "analysis.json"
    result = generate_upgrade_analysis_prompt(
        [{"package_name": "outshine",
          "repo_url": "https://github.com/alphapapa/outshine",
          "pinned_ref": "aaa", "latest_ref": "bbb",
          "diff_path": diff1, "usage_path": usage1},
         {"package_name": "outorg",
          "repo_url": "https://github.com/alphapapa/outorg",
          "pinned_ref": "ccc", "latest_ref": "ddd",
          "diff_path": diff2, "usage_path": usage2}],
        output, "",
    )
    assert str(diff1) in result
    assert str(diff2) in result
    assert str(usage1) in result
    assert str(usage2) in result
    assert "outshine" in result
    assert "outorg" in result

