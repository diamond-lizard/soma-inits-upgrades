"""Shared pytest fixtures for soma-inits-upgrades tests."""

from __future__ import annotations

import subprocess
import time
from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.state_schema import EntryState, GlobalState

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

@pytest.fixture()
def sample_stale_inits() -> list[dict[str, str]]:
    """Return a valid stale inits results list with 2 sample entries."""
    return [
        {
            "init_file": "soma-dash-init.el",
            "repo_url": "https://github.com/magnars/dash.el",
            "pinned_ref": "abc1234567890abcdef1234567890abcdef123456",
        },
        {
            "init_file": "soma-magit-init.el",
            "repo_url": "https://github.com/magit/magit",
            "pinned_ref": "def4567890abcdef1234567890abcdef12345678",
        },
    ]


@pytest.fixture()
def sample_entry_state() -> EntryState:
    """Return a default EntryState model instance."""
    return EntryState(
        init_file="soma-dash-init.el",
        repo_url="https://github.com/magnars/dash.el",
        pinned_ref="abc1234567890abcdef1234567890abcdef123456",
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


class FakePopen:
    """Fake subprocess.Popen for testing tracked_run."""

    def __init__(
        self, *, exit_code: int = 0,
        stdout: str = "", stderr: str = "",
        delay: float | None = None,
    ) -> None:
        self.returncode: int | None = None
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        self._delay = delay
        self.terminated = False
        self.killed = False
        self.pid = 12345
        self.args: list[str] = ["fake"]
        self._started = time.monotonic()

    def communicate(
        self, input: str | None = None,  # noqa: A002
        timeout: float | None = None,
    ) -> tuple[str, str]:
        """Return stdout/stderr, raising TimeoutExpired if needed."""
        if self._delay is not None:
            if timeout is not None and timeout < self._delay:
                raise subprocess.TimeoutExpired("fake", timeout)
            time.sleep(self._delay)
        self.returncode = self._exit_code
        return self._stdout, self._stderr

    def poll(self) -> int | None:
        """Return exit code if process has finished."""
        if self._delay is None:
            self.returncode = self._exit_code
            return self._exit_code
        elapsed = time.monotonic() - self._started
        if elapsed >= self._delay:
            self.returncode = self._exit_code
            return self._exit_code
        return None

    def terminate(self) -> None:
        """Record that terminate was called."""
        self.terminated = True
        self.returncode = self._exit_code

    def kill(self) -> None:
        """Record that forced stop was called."""
        self.killed = True
        self.returncode = self._exit_code

    def wait(self, timeout: float | None = None) -> int:
        """Return exit code."""
        self.returncode = self._exit_code
        return self._exit_code


def make_fake_popen(
    *, exit_code: int = 0,
    stdout: str = "", stderr: str = "",
    delay: float | None = None,
) -> FakePopen:
    """Create a FakePopen instance with configurable behavior."""
    return FakePopen(
        exit_code=exit_code, stdout=stdout,
        stderr=stderr, delay=delay,
    )
