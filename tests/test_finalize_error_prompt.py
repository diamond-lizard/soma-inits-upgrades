"""Tests for error prompt behavior in finalize_entry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from soma_inits_upgrades.processing_finalize import finalize_entry
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _repo(done_reason: str | None = None, notes: str | None = None) -> RepoState:
    """Build a RepoState with optional done_reason and notes."""
    r = RepoState(
        repo_url="https://github.com/magnars/dash.el",
        pinned_ref="abc1234567890abcdef1234567890abcdef123456",
    )
    r.done_reason = done_reason
    r.notes = notes
    return r


def _make_ctx(tmp_path: Path, repo: RepoState):
    """Build an in-progress EntryContext with one repo."""
    from runner_helpers import make_ctx
    ctx = make_ctx(tmp_path, [repo])
    ctx.entry_state.status = "in_progress"
    return ctx


def test_all_repos_error_continue_shows_details(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'c' continues; stderr shows repo URL, state path, and notes."""
    monkeypatch.setenv("FORCE_COLOR", "1")
    notes = "clone failed [origin: tasks.py:10 in do_clone]"
    ctx = _make_ctx(tmp_path, _repo("error", notes))
    ctx.input_fn = lambda _: "c"
    finalize_entry(ctx)
    assert ctx.entry_state.status == "error"
    captured = capsys.readouterr()
    assert "repo: https://github.com/magnars/dash.el" in captured.err
    assert f"state: {ctx.entry_state_path}" in captured.err
    assert "error: clone failed" in captured.err
    assert "error location: tasks.py:10 in do_clone" in captured.err
    assert "\x1b[31m" in captured.err


def test_all_repos_error_quit_exits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'q' triggers sys.exit; stderr shows repo details."""
    monkeypatch.setenv("FORCE_COLOR", "1")
    notes = "clone failed [origin: tasks.py:10 in do_clone]"
    ctx = _make_ctx(tmp_path, _repo("error", notes))
    ctx.input_fn = lambda _: "q"
    with pytest.raises(SystemExit):
        finalize_entry(ctx)
    captured = capsys.readouterr()
    assert ctx.entry_state.status == "error"
    assert "repo: https://github.com/magnars/dash.el" in captured.err
    assert f"state: {ctx.entry_state_path}" in captured.err
    assert "error: clone failed" in captured.err
    assert "error location: tasks.py:10 in do_clone" in captured.err
    assert "\x1b[31m" in captured.err
