"""Tests for validation_schema.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from soma_inits_upgrades.validation_schema import (
    StaleInitsEntry,
    StaleInitsFile,
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


def test_stale_inits_file_duplicate_pair_rejected() -> None:
    """Verify duplicate (init_file, repo_url) pairs are rejected."""
    with pytest.raises(ValidationError, match=r"duplicate.*init_file.*repo_url"):
        StaleInitsFile(results=[
            {"init_file": "a.el", "repo_url": "https://x/y", "pinned_ref": "1"},
            {"init_file": "a.el", "repo_url": "https://x/y", "pinned_ref": "2"},
        ])


def test_stale_inits_file_same_init_different_repo_accepted() -> None:
    """Verify same init_file with different repo_url is accepted."""
    f = StaleInitsFile(results=[
        {"init_file": "a.el", "repo_url": "https://x/y", "pinned_ref": "1"},
        {"init_file": "a.el", "repo_url": "https://x/z", "pinned_ref": "2"},
    ])
    assert len(f.results) == 2


def test_stale_inits_file_empty_results() -> None:
    """Verify empty results array passes validation."""
    f = StaleInitsFile(results=[])
    assert f.results == []
