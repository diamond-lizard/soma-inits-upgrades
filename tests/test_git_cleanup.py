"""Tests for git_cleanup.py."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.git_cleanup import generate_diff
from soma_inits_upgrades.subprocess_utils import SubprocessTimeoutError

if TYPE_CHECKING:
    from pathlib import Path


def _init_repo_with_diff(tmp_path: Path) -> dict[str, Path | str]:
    """Create a repo with two commits that produce a diff."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", str(repo)], check=True,
        capture_output=True)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    (repo / "file.txt").write_text("old content")
    subprocess.run(["git", "add", "file.txt"], check=True,
        capture_output=True, cwd=str(repo))
    subprocess.run(["git", "commit", "-m", "first"], check=True,
        capture_output=True, cwd=str(repo), env=env)
    r1 = subprocess.run(["git", "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True, cwd=str(repo))
    sha1 = r1.stdout.strip()
    (repo / "file.txt").write_text("new content")
    subprocess.run(["git", "add", "file.txt"], check=True,
        capture_output=True, cwd=str(repo))
    subprocess.run(["git", "commit", "-m", "second"], check=True,
        capture_output=True, cwd=str(repo), env=env)
    r2 = subprocess.run(["git", "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True, cwd=str(repo))
    sha2 = r2.stdout.strip()
    return {"repo": repo, "sha1": sha1, "sha2": sha2}


def test_generate_diff_nonempty(tmp_path: Path) -> None:
    """generate_diff writes a non-empty diff file and returns True."""
    info = _init_repo_with_diff(tmp_path)
    out = tmp_path / "output.diff"
    result = generate_diff(info["repo"], str(info["sha1"]),
        str(info["sha2"]), out)
    assert result is True
    assert out.exists()
    content = out.read_text()
    assert "old content" in content
    assert "new content" in content


def test_generate_diff_empty(tmp_path: Path) -> None:
    """generate_diff returns False for identical refs."""
    info = _init_repo_with_diff(tmp_path)
    out = tmp_path / "output.diff"
    result = generate_diff(info["repo"], str(info["sha1"]),
        str(info["sha1"]), out)
    assert result is False
    assert not out.exists()


def test_generate_diff_invalid_ref(tmp_path: Path) -> None:
    """generate_diff raises RuntimeError for invalid ref."""
    info = _init_repo_with_diff(tmp_path)
    out = tmp_path / "output.diff"
    with pytest.raises(RuntimeError, match="git diff failed"):
        generate_diff(info["repo"], "0" * 40, str(info["sha2"]), out)


def test_generate_diff_timeout(tmp_path: Path) -> None:
    """generate_diff raises RuntimeError on timeout."""
    def fake_run(*_a: object, **_kw: object) -> None:
        raise SubprocessTimeoutError(["git"], 120.0)
    out = tmp_path / "output.diff"
    with pytest.raises(RuntimeError, match="timed out"):
        generate_diff(tmp_path, "aaa", "bbb", out, run_fn=fake_run)
