"""Tests for git_ops.py."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.git_ops import (
    clone_repo,
    detect_default_branch,
    ensure_working_tree_at_ref,
    rev_parse,
    safe_rmtree,
    verify_ref,
)

if TYPE_CHECKING:
    from pathlib import Path


def _git_commit(work: Path, name: str, content: str, msg: str) -> None:
    """Create a file and commit it."""
    (work / name).write_text(content)
    subprocess.run(["git", "add", name], check=True,
        capture_output=True, cwd=str(work))
    subprocess.run(["git", "commit", "-m", msg], check=True,
        capture_output=True, cwd=str(work),
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
         "HOME": str(work), "PATH": "/usr/bin:/bin"})


def _get_head(work: Path) -> str:
    """Return HEAD SHA."""
    r = subprocess.run(["git", "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True, cwd=str(work))
    return r.stdout.strip()

@pytest.fixture()
def git_repo(tmp_path: Path) -> dict[str, Path | str]:
    """Create a bare repo with two commits and a clone."""
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True,
        capture_output=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True,
        capture_output=True)
    _git_commit(work, "first.txt", "first", "first commit")
    sha1 = _get_head(work)
    _git_commit(work, "second.txt", "second", "second commit")
    sha2 = _get_head(work)
    subprocess.run(["git", "push"], check=True, capture_output=True,
        cwd=str(work))
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(bare), str(clone)], check=True,
        capture_output=True)
    return {"bare": bare, "clone": clone, "sha1": sha1, "sha2": sha2,
        "tmp": tmp_path}


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


def test_safe_rmtree_outside_container(tmp_path: Path) -> None:
    """safe_rmtree raises ValueError when target is outside container."""
    outside = tmp_path / "outside"
    outside.mkdir()
    container = tmp_path / "container"
    container.mkdir()
    with pytest.raises(ValueError, match="not inside"):
        safe_rmtree(outside, container)


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
        # Remove symbolic HEAD to force fallback
        head_file = bare / "HEAD"
        head_file.write_text("0" * 40 + "\n")
        clone = tmp_path / "clone"
        subprocess.run(["git", "clone", str(bare), str(clone)],
            check=True, capture_output=True)
        branch = detect_default_branch(clone)
        assert branch in ("main", "master")

    def test_rev_parse_invalid_branch(self, git_repo: dict) -> None:
        """rev_parse returns None for nonexistent branch."""
        assert rev_parse(git_repo["clone"], "nonexistent") is None

    def test_ensure_working_tree_bad_ref(self, git_repo: dict) -> None:
        """ensure_working_tree_at_ref returns False for bad ref."""
        ok = ensure_working_tree_at_ref(git_repo["clone"], "0" * 40)
        assert ok is False
