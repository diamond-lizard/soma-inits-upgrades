"""Test that generate_diff preserves embedded carriage return bytes."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.git_cleanup import generate_diff

if TYPE_CHECKING:
    from pathlib import Path


def test_generate_diff_preserves_cr_bytes(tmp_path: Path) -> None:
    """generate_diff preserves embedded CR bytes from git output."""
    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo)], check=True, capture_output=True,
    )
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "HOME": str(tmp_path), "PATH": "/usr/bin:/bin",
    }
    (repo / "file.el").write_text("(defun hello () nil)\n")
    subprocess.run(
        ["git", "add", "file.el"],
        check=True, capture_output=True, cwd=str(repo),
    )
    subprocess.run(
        ["git", "commit", "-m", "first"],
        check=True, capture_output=True, cwd=str(repo), env=env,
    )
    r1 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, cwd=str(repo),
    )
    sha1 = r1.stdout.strip()
    cr = b"\r"
    content = b'(replace-regexp-in-string "' + cr + b'" "")\n'
    (repo / "file.el").write_bytes(content)
    subprocess.run(
        ["git", "add", "file.el"],
        check=True, capture_output=True, cwd=str(repo),
    )
    subprocess.run(
        ["git", "commit", "-m", "add-cr"],
        check=True, capture_output=True, cwd=str(repo), env=env,
    )
    r2 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, cwd=str(repo),
    )
    sha2 = r2.stdout.strip()
    out = tmp_path / "output.diff"
    result = generate_diff(repo, sha1, sha2, out)
    assert result is True
    raw = out.read_bytes()
    assert cr in raw
