"""Edge case and error path tests for git operations."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.git_ref_ops import (
    detect_default_branch,
    rev_parse,
    verify_ref,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestEdgeCases:
    """Edge case tests for git operations."""

    def test_detect_branch_with_slashes(self, tmp_path: Path) -> None:
        """detect_default_branch handles branch names with slashes."""
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
        subprocess.run(["git", "branch", "-m", "feature/main"],
            check=True, capture_output=True, cwd=str(bare))
        subprocess.run(
            ["git", "symbolic-ref", "HEAD",
             "refs/heads/feature/main"],
            check=True, capture_output=True, cwd=str(bare))
        clone = tmp_path / "clone"
        subprocess.run(["git", "clone", str(bare), str(clone)],
            check=True, capture_output=True)
        branch = detect_default_branch(clone)
        assert branch == "feature/main"

    def test_verify_ref_with_tag(self, git_repo: dict) -> None:
        """verify_ref returns True for annotated tags."""
        clone = git_repo["clone"]
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(clone), "PATH": "/usr/bin:/bin"}
        subprocess.run(
            ["git", "tag", "-a", "v1.0", "-m", "release"],
            check=True, capture_output=True,
            cwd=str(clone), env=env,
        )
        assert verify_ref(clone, "v1.0") is True

    def test_blobless_clone_operations(self, tmp_path: Path,
        git_repo: dict) -> None:
        """rev_parse and verify_ref work in a blobless clone."""
        blobless = tmp_path / "blobless"
        subprocess.run(
            ["git", "clone", "--filter=blob:none",
             str(git_repo["bare"]), str(blobless)],
            check=True, capture_output=True,
        )
        branch = detect_default_branch(blobless)
        assert branch is not None
        sha = rev_parse(blobless, branch)
        assert sha == git_repo["sha2"]
        assert verify_ref(blobless, str(git_repo["sha1"])) is True

