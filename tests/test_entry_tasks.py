"""Tests for entry_tasks.py: git task handlers with fake subprocess."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.entry_tasks import (
    task_clone,
    task_default_branch,
    task_diff,
    task_latest_ref,
)
from soma_inits_upgrades.protocols import EntryContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(tmp_path: Path, **git_kw: object) -> EntryContext:
    """Build an EntryContext with fake git and temp dirs."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True, exist_ok=True)
    td = tmp_path / ".tmp"
    td.mkdir(exist_ok=True)
    es = EntryState(init_file="x.el", repo_url="https://x.com/r", pinned_ref="old")
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    return EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem="x",
        results=[{"init_file": "x.el", "repo_url": "https://x.com/r", "pinned_ref": "old"}],
        xclip_checker=lambda: False, run_fn=make_fake_git(**git_kw),
    )


def test_clone_happy(tmp_path: Path) -> None:
    """Clone succeeds and task is marked complete."""
    ctx = _ctx(tmp_path, clone_ok=True)
    task_clone(ctx)
    assert ctx.entry_state.tasks_completed["clone"] is True


def test_clone_failure(tmp_path: Path) -> None:
    """Clone failure sets entry to error."""
    ctx = _ctx(tmp_path, clone_ok=False)
    task_clone(ctx)
    assert ctx.entry_state.status == "error"
    assert ctx.entry_state.notes is not None
    assert "clone failed" in ctx.entry_state.notes


def test_branch_detection_failure(tmp_path: Path) -> None:
    """Branch detection failure sets entry to error."""
    ctx = _ctx(tmp_path, clone_ok=True, branch=None, latest_ref=None)
    ctx.entry_state.tasks_completed["clone"] = True
    (ctx.tmp_dir / ctx.init_stem).mkdir()
    task_default_branch(ctx)
    assert ctx.entry_state.status == "error"


def test_pinned_ref_not_found(tmp_path: Path) -> None:
    """Missing pinned ref sets entry to error."""
    ctx = _ctx(tmp_path, ref_exists=False)
    ctx.entry_state.tasks_completed["clone"] = True
    ctx.entry_state.tasks_completed["default_branch"] = True
    ctx.entry_state.default_branch = "main"
    (ctx.tmp_dir / ctx.init_stem).mkdir()
    task_latest_ref(ctx)
    assert ctx.entry_state.status == "error"
    assert "does not exist" in (ctx.entry_state.notes or "")


def test_empty_diff(tmp_path: Path) -> None:
    """Empty diff marks entry done with appropriate reason."""
    ctx = _ctx(tmp_path, diff_output="")
    ctx.entry_state.tasks_completed["clone"] = True
    ctx.entry_state.tasks_completed["default_branch"] = True
    ctx.entry_state.tasks_completed["latest_ref"] = True
    ctx.entry_state.default_branch = "main"
    ctx.entry_state.pinned_ref = "old"
    ctx.entry_state.latest_ref = "new"
    (ctx.tmp_dir / ctx.init_stem).mkdir()
    task_diff(ctx)
    assert ctx.entry_state.status == "done"
    assert ctx.entry_state.done_reason == "empty_diff"
