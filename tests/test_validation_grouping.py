"""Tests for input validation and grouping pipeline."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from soma_inits_upgrades.cli_helpers import load_stale_inits
from soma_inits_upgrades.validation_schema import StaleInitsFile

if TYPE_CHECKING:
    from pathlib import Path


def test_same_init_different_repos_accepted() -> None:
    """(a) Two entries sharing init_file with different repo_url pass."""
    f = StaleInitsFile(results=[
        {"init_file": "a.el", "repo_url": "https://x.com/o/r1", "pinned_ref": "a1"},
        {"init_file": "a.el", "repo_url": "https://x.com/o/r2", "pinned_ref": "b2"},
    ])
    assert len(f.results) == 2


def test_duplicate_pair_rejected() -> None:
    """(b) Duplicate (init_file, repo_url) pair is rejected."""
    with pytest.raises(ValidationError, match=r"duplicate.*init_file.*repo_url"):
        StaleInitsFile(results=[
            {"init_file": "a.el", "repo_url": "https://x.com/o/r", "pinned_ref": "a1"},
            {"init_file": "a.el", "repo_url": "https://x.com/o/r", "pinned_ref": "b2"},
        ])


def _write_input(path: Path, entries: list[dict[str, str]]) -> None:
    """Write a stale inits JSON file."""
    path.write_text(json.dumps({"results": entries}))


def test_load_stale_inits_groups_by_init_file(tmp_path: Path) -> None:
    """(c) load_stale_inits produces one entry per unique init_file."""
    path = tmp_path / "stale.json"
    _write_input(path, [
        {"init_file": "a.el", "repo_url": "https://x.com/o/r1", "pinned_ref": "a1"},
        {"init_file": "a.el", "repo_url": "https://x.com/o/r2", "pinned_ref": "b2"},
        {"init_file": "b.el", "repo_url": "https://x.com/o/r3", "pinned_ref": "c3"},
    ])
    grouped = load_stale_inits(path)
    assert len(grouped) == 2
    names = [g["init_file"] for g in grouped]
    assert "a.el" in names
    assert "b.el" in names


def test_grouped_entry_has_two_repos(tmp_path: Path) -> None:
    """(d) Grouped entry with two repos has repos list of length 2."""
    path = tmp_path / "stale.json"
    _write_input(path, [
        {"init_file": "a.el", "repo_url": "https://x.com/o/r1", "pinned_ref": "a1"},
        {"init_file": "a.el", "repo_url": "https://x.com/o/r2", "pinned_ref": "b2"},
    ])
    grouped = load_stale_inits(path)
    assert len(grouped) == 1
    entry = grouped[0]
    assert entry["init_file"] == "a.el"
    assert len(entry["repos"]) == 2
    urls = {r["repo_url"] for r in entry["repos"]}
    assert urls == {"https://x.com/o/r1", "https://x.com/o/r2"}
