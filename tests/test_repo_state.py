"""Tests for RepoState model construction, defaults, and tier1 tracking."""

from __future__ import annotations

from soma_inits_upgrades.state_schema import RepoState


def test_repo_state_defaults() -> None:
    """Verify RepoState defaults for optional fields."""
    repo = RepoState(repo_url="https://github.com/org/pkg", pinned_ref="abc123")
    assert repo.repo_url == "https://github.com/org/pkg"
    assert repo.pinned_ref == "abc123"
    assert repo.latest_ref is None
    assert repo.default_branch is None
    assert repo.package_name is None
    assert repo.min_emacs_version is None
    assert repo.emacs_upgrade_required is False
    assert repo.depends_on is None
    assert repo.done_reason is None
    assert repo.notes is None


def test_repo_state_tier1_tasks_completed_keys() -> None:
    """Verify tier1_tasks_completed has all expected keys, all False."""
    repo = RepoState(repo_url="https://github.com/org/pkg", pinned_ref="abc123")
    expected_keys = [
        "clone", "default_branch", "latest_ref", "diff",
        "deps", "version_check", "symbols",
    ]
    assert list(repo.tier1_tasks_completed.keys()) == expected_keys
    assert all(v is False for v in repo.tier1_tasks_completed.values())


def test_repo_state_tier1_tasks_independent() -> None:
    """Verify each RepoState gets its own tier1_tasks_completed dict."""
    repo_a = RepoState(repo_url="https://github.com/a/a", pinned_ref="aaa")
    repo_b = RepoState(repo_url="https://github.com/b/b", pinned_ref="bbb")
    repo_a.tier1_tasks_completed["clone"] = True
    assert repo_b.tier1_tasks_completed["clone"] is False
