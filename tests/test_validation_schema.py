"""Tests for validation_schema.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from soma_inits_upgrades.validation_schema import (
    StaleInitsEntry,
    StaleInitsFile,
    UpgradeAnalysis,
    strip_code_fences,
)


def test_stale_inits_entry_valid() -> None:
    """Verify valid entry passes."""
    entry = StaleInitsEntry(
        init_file="a.el",
        repo_url="https://github.com/x/y",
        pinned_ref="abc123",
    )
    assert entry.init_file == "a.el"


def test_stale_inits_entry_http_rejected() -> None:
    """Verify http:// scheme is rejected."""
    with pytest.raises(ValidationError):
        StaleInitsEntry(
            init_file="a.el", repo_url="http://github.com/x/y", pinned_ref="abc",
        )


def test_stale_inits_entry_empty_hostname_rejected() -> None:
    """Verify empty hostname is rejected."""
    with pytest.raises(ValidationError):
        StaleInitsEntry(
            init_file="a.el", repo_url="https://", pinned_ref="abc",
        )


def test_stale_inits_entry_non_url_rejected() -> None:
    """Verify non-URL string is rejected."""
    with pytest.raises(ValidationError):
        StaleInitsEntry(
            init_file="a.el", repo_url="not-a-url", pinned_ref="abc",
        )


def test_pinned_ref_dash_rejected() -> None:
    """Verify pinned_ref starting with - is rejected."""
    with pytest.raises(ValidationError):
        StaleInitsEntry(
            init_file="a.el", repo_url="https://github.com/x/y",
            pinned_ref="-malicious",
        )


def test_pinned_ref_empty_rejected() -> None:
    """Verify empty pinned_ref is rejected."""
    with pytest.raises(ValidationError):
        StaleInitsEntry(
            init_file="a.el", repo_url="https://github.com/x/y", pinned_ref="",
        )


def test_stale_inits_file_duplicate_rejected() -> None:
    """Verify duplicate init_file values are rejected."""
    with pytest.raises(ValidationError):
        StaleInitsFile(results=[
            {"init_file": "a.el", "repo_url": "https://x/y", "pinned_ref": "1"},
            {"init_file": "a.el", "repo_url": "https://x/z", "pinned_ref": "2"},
        ])


def test_stale_inits_file_empty_results() -> None:
    """Verify empty results array passes validation."""
    f = StaleInitsFile(results=[])
    assert f.results == []


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
