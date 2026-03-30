"""Shared pytest fixtures for soma-inits-upgrades tests."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

@pytest.fixture()
def sample_stale_inits() -> list[dict[str, object]]:
    """Return a valid stale inits results list with 2 sample entries."""
    return [
        {"init_file": "soma-dash-init.el", "repos": [
            {"repo_url": "https://github.com/magnars/dash.el",
             "pinned_ref": "abc1234567890abcdef1234567890abcdef123456"},
        ]},
        {"init_file": "soma-magit-init.el", "repos": [
            {"repo_url": "https://github.com/magit/magit",
             "pinned_ref": "def4567890abcdef1234567890abcdef12345678"},
        ]},
    ]


@pytest.fixture()
def sample_entry_state() -> EntryState:
    """Return a default EntryState model instance."""
    return EntryState(
        init_file="soma-dash-init.el",
        repos=[RepoState(
            repo_url="https://github.com/magnars/dash.el",
            pinned_ref="abc1234567890abcdef1234567890abcdef123456",
        )],
    )


@pytest.fixture()
def sample_global_state() -> GlobalState:
    """Return a default GlobalState model instance."""
    return GlobalState()


@pytest.fixture()
def output_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary output directory with .state/ and .tmp/ subdirectories."""
    state_dir = tmp_path / ".state"
    tmp_dir = tmp_path / ".tmp"
    state_dir.mkdir()
    tmp_dir.mkdir()
    yield tmp_path


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


@pytest.fixture(autouse=True)
def _disable_xclip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from writing to the X primary selection."""
    monkeypatch.setattr(
        "soma_inits_upgrades.clipboard.copy_to_primary",
        lambda text, run_fn=subprocess.run: None,
    )
