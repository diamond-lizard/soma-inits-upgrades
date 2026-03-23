"""Tests for git_ops.py."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.git_ops import clone_repo, safe_rmtree

if TYPE_CHECKING:
    from pathlib import Path


def test_clone_repo_success(tmp_path: Path, git_repo: dict) -> None:
    """Clone succeeds and target directory is created."""
    target = tmp_path / "newclone"
    ok, err = clone_repo(str(git_repo["bare"]), target, tmp_path)
    assert ok is True
    assert err == ""
    assert (target / ".git").is_dir()


def test_clone_repo_replaces_existing(tmp_path: Path, git_repo: dict) -> None:
    """Clone replaces an existing target directory."""
    target = tmp_path / "newclone"
    target.mkdir()
    (target / "stale").write_text("old")
    ok, _ = clone_repo(str(git_repo["bare"]), target, tmp_path)
    assert ok is True
    assert not (target / "stale").exists()


def test_clone_repo_failure(tmp_path: Path) -> None:
    """Clone fails with nonexistent repo URL."""
    target = tmp_path / "newclone"
    fake_url = str(tmp_path / "no-such-repo")
    ok, err = clone_repo(fake_url, target, tmp_path)
    assert ok is False
    assert "clone failed" in err


def test_clone_repo_timeout(tmp_path: Path) -> None:
    """Clone timeout cleans up partial directory."""
    target = tmp_path / "newclone"
    def fake_run(*_args: object, **_kw: object) -> None:
        target.mkdir(exist_ok=True)
        raise subprocess.TimeoutExpired(cmd="git", timeout=60)
    ok, err = clone_repo("http://x", target, tmp_path, run_fn=fake_run)
    assert ok is False
    assert "timed out" in err
    assert not target.exists()




def test_safe_rmtree_outside_container(tmp_path: Path) -> None:
    """safe_rmtree raises ValueError when target is outside container."""
    outside = tmp_path / "outside"
    outside.mkdir()
    container = tmp_path / "container"
    container.mkdir()
    with pytest.raises(ValueError, match="not inside"):
        safe_rmtree(outside, container)
