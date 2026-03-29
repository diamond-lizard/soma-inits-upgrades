"""Tests for clone_cleanup and task_temp_cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks_diff import clone_cleanup, task_temp_cleanup

if TYPE_CHECKING:
    from pathlib import Path


def _make_entry_ctx(
    output_dir: Path, init_stem: str = "soma-dash-init",
) -> tuple:
    """Build minimal EntryContext and RepoContext for cleanup tests."""
    from soma_inits_upgrades.protocols import EntryContext, RepoContext
    from soma_inits_upgrades.state_schema import (
        EntryState,
        GlobalState,
        RepoState,
    )
    repo_url = "https://github.com/magnars/dash.el"
    repo_state = RepoState(repo_url=repo_url, pinned_ref="abc123")
    state = EntryState(
        init_file=f"{init_stem}.el", repos=[repo_state],
    )
    state_path = output_dir / ".state" / f"{init_stem}.el.json"
    global_state = GlobalState()
    tmp_dir = output_dir / ".tmp" / init_stem
    ctx = EntryContext(
        entry_state=state,
        entry_state_path=state_path,
        global_state=global_state,
        global_state_path=output_dir / ".state" / "global.json",
        entry_idx=1, total=1,
        output_dir=output_dir,
        tmp_dir=tmp_dir,
        state_dir=output_dir / ".state",
        init_stem=init_stem,
        results=[],
        xclip_checker=lambda: False,
        run_fn=_noop_run,
    )
    repo_temp = tmp_dir / "magnars--dash.el"
    repo_ctx = RepoContext(
        entry_ctx=ctx, repo_state=repo_state,
        temp_dir=repo_temp,
        clone_dir=repo_temp / "clone",
    )
    return ctx, repo_ctx


def _noop_run(args: list[str] | str, **kw: object) -> object:
    """No-op subprocess runner."""
    raise NotImplementedError


def test_clone_cleanup_removes_clone_dir(output_dir: Path) -> None:
    """clone_cleanup removes the clone directory when it exists."""
    _, repo_ctx = _make_entry_ctx(output_dir)
    repo_ctx.clone_dir.mkdir(parents=True)
    (repo_ctx.clone_dir / "HEAD").write_text("ref")
    clone_cleanup(repo_ctx)
    assert not repo_ctx.clone_dir.exists()


def test_clone_cleanup_noop_when_absent(output_dir: Path) -> None:
    """clone_cleanup is a no-op when the clone directory is absent."""
    _, repo_ctx = _make_entry_ctx(output_dir)
    clone_cleanup(repo_ctx)


def test_task_temp_cleanup_removes_temp_dir(output_dir: Path) -> None:
    """task_temp_cleanup removes the per-init-file temp directory."""
    from soma_inits_upgrades.state import atomic_write_json
    ctx, _ = _make_entry_ctx(output_dir)
    ctx.tmp_dir.mkdir(parents=True, exist_ok=True)
    (ctx.tmp_dir / "artifact.txt").write_text("data")
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    task_temp_cleanup(ctx)
    assert not ctx.tmp_dir.exists()
    assert ctx.entry_state.tasks_completed["temp_cleanup"] is True


def test_task_temp_cleanup_idempotent(output_dir: Path) -> None:
    """task_temp_cleanup is a no-op on second call (already marked done)."""
    from soma_inits_upgrades.state import atomic_write_json
    ctx, _ = _make_entry_ctx(output_dir)
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    task_temp_cleanup(ctx)
    task_temp_cleanup(ctx)
    assert ctx.entry_state.tasks_completed["temp_cleanup"] is True
