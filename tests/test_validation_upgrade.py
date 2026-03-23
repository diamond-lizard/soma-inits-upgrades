"""Tests for UpgradeAnalysis model and strip_code_fences helper."""

from __future__ import annotations

from soma_inits_upgrades.validation_schema import (
    UpgradeAnalysis,
    strip_code_fences,
)


def test_upgrade_analysis_defaults() -> None:
    """Verify all-defaults construction works."""
    ua = UpgradeAnalysis()
    assert ua.breaking_api_changes == []
    assert ua.change_summary == ""
    assert ua.emacs_version_conflict is False


def test_upgrade_analysis_extra_keys() -> None:
    """Verify extra='allow' accepts unexpected keys."""
    ua = UpgradeAnalysis.model_validate({"extra_field": "value"})
    assert ua.change_summary == ""


def test_upgrade_analysis_alias() -> None:
    """Verify AliasChoices maps breaking_changes to breaking_api_changes."""
    ua = UpgradeAnalysis.model_validate(
        {"breaking_changes": [{"desc": "x"}]},
    )
    assert len(ua.breaking_api_changes) == 1


def test_strip_code_fences_json() -> None:
    """Verify removal of json code fences."""
    fenced = "```json\n{\"a\": 1}\n```"
    assert strip_code_fences(fenced) == '{"a": 1}'


def test_strip_code_fences_bare() -> None:
    """Verify removal of bare code fences."""
    fenced = "```\n{\"a\": 1}\n```"
    assert strip_code_fences(fenced) == '{"a": 1}'


def test_strip_code_fences_noop() -> None:
    """Verify no-op when no fences present."""
    assert strip_code_fences('{"a": 1}') == '{"a": 1}'


def test_strip_code_fences_internal_backticks() -> None:
    """Verify content with backticks that isn't a fence is unchanged."""
    text = 'some ``` in the middle'
    assert strip_code_fences(text) == text
