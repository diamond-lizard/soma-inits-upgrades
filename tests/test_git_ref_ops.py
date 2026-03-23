"""Tests for git_ref_ops.py: branch detection, rev-parse, ref verification."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.git_ref_ops import (
    detect_default_branch,
    ensure_working_tree_at_ref,
    rev_parse,
    verify_ref,
)

if TYPE_CHECKING:
    from pathlib import Path


def _get_head(work: Path) -> str:
    """Return HEAD SHA."""
    r = subprocess.run(["git", "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True, cwd=str(work))
    return r.stdout.strip()

def test_detect_default_branch(git_repo: dict) -> None:
    """Detect default branch from a standard clone."""
    branch = detect_default_branch(git_repo["clone"])
    assert branch in ("main", "master")


def test_rev_parse(git_repo: dict) -> None:
    """Rev-parse returns a 40-char hex SHA."""
    branch = detect_default_branch(git_repo["clone"])
    sha = rev_parse(git_repo["clone"], branch)
    assert sha is not None
    assert len(sha) == 40
    assert sha == git_repo["sha2"]


def test_verify_ref_exists(git_repo: dict) -> None:
    """verify_ref returns True for a known SHA."""
    assert verify_ref(git_repo["clone"], str(git_repo["sha1"])) is True


def test_verify_ref_missing(git_repo: dict) -> None:
    """verify_ref returns False for a nonexistent ref."""
    assert verify_ref(git_repo["clone"], "0" * 40) is False


def test_ensure_working_tree_at_ref(git_repo: dict) -> None:
    """ensure_working_tree_at_ref checks out the given SHA."""
    ok = ensure_working_tree_at_ref(git_repo["clone"], str(git_repo["sha1"]))
    assert ok is True
    head = _get_head(git_repo["clone"])
    assert head == git_repo["sha1"]


def test_rev_parse_invalid_branch(git_repo: dict) -> None:
    """rev_parse returns None for nonexistent branch."""
    assert rev_parse(git_repo["clone"], "nonexistent") is None


def test_ensure_working_tree_bad_ref(git_repo: dict) -> None:
    """ensure_working_tree_at_ref returns False for bad ref."""
    ok = ensure_working_tree_at_ref(git_repo["clone"], "0" * 40)
    assert ok is False


class TestErrorPaths:
    """Error path tests using real git."""

    def test_detect_branch_detached_head(self, tmp_path: Path) -> None:
        """Fallback to main/master when symbolic-ref fails."""
        bare = tmp_path / "bare.git"
        subprocess.run(["git", "init", "--bare", str(bare)],
            check=True, capture_output=True)
        work = tmp_path / "work"
        subprocess.run(["git", "clone", str(bare), str(work)],
            check=True, capture_output=True)
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
        (work / "f.txt").write_text("x")
        subprocess.run(["git", "add", "f.txt"], check=True,
            capture_output=True, cwd=str(work))
        subprocess.run(["git", "commit", "-m", "init"], check=True,
            capture_output=True, cwd=str(work), env=env)
        subprocess.run(["git", "push"], check=True,
            capture_output=True, cwd=str(work))
        head_file = bare / "HEAD"
        head_file.write_text("0" * 40 + "\n")
        clone = tmp_path / "clone"
        subprocess.run(["git", "clone", str(bare), str(clone)],
            check=True, capture_output=True)
        branch = detect_default_branch(clone)
        assert branch in ("main", "master")
