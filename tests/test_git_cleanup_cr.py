"""Test that generate_diff preserves embedded carriage return bytes."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.git_cleanup import generate_diff

if TYPE_CHECKING:
    from pathlib import Path


def _init_cr_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """Create a git repo with a CR-containing file. Returns (repo, sha1, sha2)."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "HOME": str(tmp_path), "PATH": "/usr/bin:/bin",
    }
    run = subprocess.run
    (repo / "file.el").write_text("(defun hello () nil)\n")
    run(["git", "add", "file.el"], check=True, capture_output=True, cwd=str(repo))
    run(["git", "commit", "-m", "first"], check=True, capture_output=True, cwd=str(repo), env=env)
    r1 = run(
        ["git", "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, cwd=str(repo),
    )
    sha1 = r1.stdout.strip()
    content = b'(replace-regexp-in-string "\r" "")\n'
    (repo / "file.el").write_bytes(content)
    run(["git", "add", "file.el"], check=True, capture_output=True, cwd=str(repo))
    run(["git", "commit", "-m", "add-cr"], check=True, capture_output=True, cwd=str(repo), env=env)
    r2 = run(
        ["git", "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, cwd=str(repo),
    )
    return repo, sha1, r2.stdout.strip()

def test_generate_diff_preserves_cr_bytes(tmp_path: Path) -> None:
    """generate_diff preserves embedded CR bytes from git output."""
    repo, sha1, sha2 = _init_cr_repo(tmp_path)
    out = tmp_path / "output.diff"
    result = generate_diff(repo, sha1, sha2, out)
    assert result is True
    raw = out.read_bytes()
    assert b"\r" in raw


def test_generate_diff_cr_with_tracked_run(tmp_path: Path) -> None:
    """generate_diff works with tracked_run (production wiring)."""
    from functools import partial

    from soma_inits_upgrades.subprocess_tracking import tracked_run
    from soma_inits_upgrades.subprocess_utils import ProcessTracker
    tracker = ProcessTracker()
    run_fn = partial(tracked_run, tracker=tracker)
    repo, sha1, sha2 = _init_cr_repo(tmp_path)
    out = tmp_path / "output.diff"
    result = generate_diff(repo, sha1, sha2, out, run_fn=run_fn)
    assert result is True
    assert b"\r" in out.read_bytes()
