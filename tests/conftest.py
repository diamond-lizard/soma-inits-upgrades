"""Shared pytest fixtures for soma-inits-upgrades tests."""

from __future__ import annotations

import subprocess
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


def make_completed_process(
    returncode: int = 0, stdout: str = "", stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Create a subprocess.CompletedProcess with configurable fields."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr,
    )


class FakeGit:
    """Fake git subprocess runner with configurable behavior and call recording."""

    def __init__(
        self, *, clone_ok: bool = True, branch: str | None = "main",
        latest_ref: str | None = "abc123", ref_exists: bool = True,
        diff_output: str = "diff content", checkout_ok: bool = True,
    ) -> None:
        """Initialize with configurable git behavior."""
        self.clone_ok = clone_ok
        self.branch = branch
        self.latest_ref = latest_ref
        self.ref_exists = ref_exists
        self.diff_output = diff_output
        self.checkout_ok = checkout_ok
        self.operations: list[tuple[str, list[str]]] = []

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Dispatch on git subcommand and return appropriate result."""
        arg_list = args if isinstance(args, list) else args.split()
        subcmd = _find_git_subcmd(arg_list)
        self.operations.append((subcmd, arg_list))
        return self._dispatch(subcmd)

    def _dispatch(self, subcmd: str) -> subprocess.CompletedProcess[str]:
        """Route to the appropriate handler based on git subcommand."""
        handlers: dict[str, subprocess.CompletedProcess[str]] = {
            "clone": make_completed_process(0 if self.clone_ok else 128),
            "symbolic-ref": self._symbolic_ref_result(),
            "rev-parse": self._rev_parse_result(),
            "cat-file": make_completed_process(0 if self.ref_exists else 1),
            "diff": make_completed_process(stdout=self.diff_output),
            "checkout": make_completed_process(0 if self.checkout_ok else 1),
        }
        return handlers.get(subcmd, make_completed_process(1, stderr="unknown command"))

    def _symbolic_ref_result(self) -> subprocess.CompletedProcess[str]:
        """Return result for symbolic-ref command."""
        if self.branch is None:
            return make_completed_process(128, stderr="not a symbolic ref")
        return make_completed_process(stdout=f"refs/remotes/origin/{self.branch}\n")

    def _rev_parse_result(self) -> subprocess.CompletedProcess[str]:
        """Return result for rev-parse command."""
        if self.latest_ref is None:
            return make_completed_process(128, stderr="unknown revision")
        return make_completed_process(stdout=f"{self.latest_ref}\n")


def _find_git_subcmd(args: list[str]) -> str:
    """Extract the git subcommand from an argument list."""
    for arg in args:
        if arg != "git" and not arg.startswith("-"):
            return arg
    return "unknown"


def make_fake_git(**kwargs: object) -> FakeGit:
    """Factory for creating FakeGit instances with configurable behavior."""
    return FakeGit(**kwargs)  # type: ignore[arg-type]



def _build_rg_match_record(symbol: str, fpath: str) -> str:
    """Build a single ripgrep JSON match record."""
    import json
    record = {
        "type": "match",
        "data": {
            "path": {"text": fpath},
            "submatches": [{"match": {"text": symbol}}],
        },
    }
    return json.dumps(record)

class FakeRg:
    """Fake ripgrep subprocess runner with configurable matches."""

    def __init__(self, matches: dict[str, list[str]] | None = None) -> None:
        """Initialize with symbol-to-files mapping."""
        self.matches = matches or {}
        self.operations: list[tuple[str, list[str]]] = []

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Simulate ripgrep JSON output."""
        arg_list = args if isinstance(args, list) else args.split()
        self.operations.append(("rg", arg_list))
        lines = [
            _build_rg_match_record(sym, fp)
            for sym, files in self.matches.items()
            for fp in files
        ]
        rc = 0 if lines else 1
        return make_completed_process(rc, stdout="\n".join(lines))


def make_fake_rg(matches: dict[str, list[str]] | None = None) -> FakeRg:
    """Factory for creating FakeRg instances."""
    return FakeRg(matches)


class FakeXclip:
    """Fake xclip runner that records calls."""

    def __init__(self) -> None:
        """Initialize call recorder."""
        self.calls: list[tuple[list[str], str]] = []

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Record the call and return success."""
        arg_list = args if isinstance(args, list) else args.split()
        input_text = str(kwargs.get("input", ""))
        self.calls.append((arg_list, input_text))
        return make_completed_process()


def make_fake_xclip() -> FakeXclip:
    """Factory for creating FakeXclip instances."""
    return FakeXclip()
