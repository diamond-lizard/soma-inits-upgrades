"""Format contract tests: document exact git output format for fake calibration."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.git_ref_ops import detect_default_branch

if TYPE_CHECKING:
    from pathlib import Path


class TestFormatContracts:
    """Document exact git output format for fake calibration."""

    def test_symbolic_ref_format(self, git_repo: dict) -> None:
        """symbolic-ref stdout ends with newline, contains full refpath."""
        r = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, cwd=str(git_repo["clone"]),
        )
        assert r.returncode == 0
        assert r.stdout.endswith("\n")
        assert "refs/remotes/origin/" in r.stdout

    def test_rev_parse_format(self, git_repo: dict) -> None:
        """rev-parse stdout is a 40-char hex SHA followed by newline."""
        branch = detect_default_branch(git_repo["clone"])
        r = subprocess.run(
            ["git", "rev-parse", f"origin/{branch}"],
            capture_output=True, text=True, cwd=str(git_repo["clone"]),
        )
        assert r.returncode == 0
        assert r.stdout.endswith("\n")
        stripped = r.stdout.strip()
        assert len(stripped) == 40
        assert all(c in "0123456789abcdef" for c in stripped)

    def test_cat_file_format(self, git_repo: dict) -> None:
        """cat-file -t returns object type followed by newline."""
        r = subprocess.run(
            ["git", "cat-file", "-t", str(git_repo["sha1"])],
            capture_output=True, text=True, cwd=str(git_repo["clone"]),
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "commit"

    def test_clone_progress_on_stderr(self, tmp_path: Path,
        git_repo: dict) -> None:
        """Clone progress goes to stderr, not stdout."""
        target = tmp_path / "fmtclone"
        r = subprocess.run(
            ["git", "clone", str(git_repo["bare"]), str(target)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert r.stdout == ""
