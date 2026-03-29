"""Tests for entry_tasks.py: git task handlers with fake subprocess."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.entry_tasks import (
    task_clone,
    task_default_branch,
)
from soma_inits_upgrades.entry_tasks_diff import task_diff
from soma_inits_upgrades.entry_tasks_ref import task_latest_ref
from soma_inits_upgrades.protocols import EntryContext, RepoContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(tmp_path: Path, **git_kw: object) -> RepoContext:
    """Build a RepoContext with fake git and temp dirs."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True, exist_ok=True)
    td = tmp_path / ".tmp"
    td.mkdir(exist_ok=True)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="old",
        )],
    )
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    entry_ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem="x",
        results=[{
            "init_file": "x.el",
            "repos": [{"repo_url": "https://forge.test/r", "pinned_ref": "old"}],
        }],
        xclip_checker=lambda: False, run_fn=make_fake_git(**git_kw),
    )
    return RepoContext(
        entry_ctx=entry_ctx, repo_state=es.repos[0],
        temp_dir=td, clone_dir=td / "x",
    )


def test_clone_happy(tmp_path: Path) -> None:
    """Clone succeeds and task is marked complete."""
    repo_ctx = _ctx(tmp_path, clone_ok=True)
    task_clone(repo_ctx)
    assert repo_ctx.repo_state.tier1_tasks_completed["clone"] is True


def test_clone_failure(tmp_path: Path) -> None:
    """Clone failure sets repo to error."""
    repo_ctx = _ctx(tmp_path, clone_ok=False)
    task_clone(repo_ctx)
    assert repo_ctx.repo_state.done_reason == "error"
    assert repo_ctx.repo_state.notes is not None
    assert "clone failed" in repo_ctx.repo_state.notes


def test_branch_detection_failure(tmp_path: Path) -> None:
    """Branch detection failure sets repo to error."""
    repo_ctx = _ctx(tmp_path, clone_ok=True, branch=None, latest_ref=None)
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    repo_ctx.clone_dir.mkdir()
    task_default_branch(repo_ctx)
    assert repo_ctx.repo_state.done_reason == "error"


def test_pinned_ref_not_found(tmp_path: Path) -> None:
    """Missing pinned ref sets repo to error."""
    repo_ctx = _ctx(tmp_path, ref_exists=False)
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    repo_ctx.repo_state.tier1_tasks_completed["default_branch"] = True
    repo_ctx.repo_state.default_branch = "main"
    repo_ctx.clone_dir.mkdir()
    task_latest_ref(repo_ctx)
    assert repo_ctx.repo_state.done_reason == "error"
    assert "does not exist" in (repo_ctx.repo_state.notes or "")


def test_empty_diff(tmp_path: Path) -> None:
    """Empty diff marks repo with done_reason."""
    repo_ctx = _ctx(tmp_path, diff_output="")
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    repo_ctx.repo_state.tier1_tasks_completed["default_branch"] = True
    repo_ctx.repo_state.tier1_tasks_completed["latest_ref"] = True
    repo_ctx.repo_state.default_branch = "main"
    repo_ctx.repo_state.pinned_ref = "old"
    repo_ctx.repo_state.latest_ref = "new"
    repo_ctx.clone_dir.mkdir()
    task_diff(repo_ctx)
    assert repo_ctx.repo_state.done_reason == "empty_diff"
