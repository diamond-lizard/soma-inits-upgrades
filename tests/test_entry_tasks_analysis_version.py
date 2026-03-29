"""Tests for entry_tasks_analysis.py: version check task handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.entry_tasks_analysis import task_version_check
from soma_inits_upgrades.protocols import EntryContext, RepoContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(tmp_path: Path) -> RepoContext:
    """Build a RepoContext for version check tests."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True, exist_ok=True)
    td = tmp_path / ".tmp"
    td.mkdir(exist_ok=True)
    es = EntryState(
        init_file="soma-pkg-init.el",
        repos=[RepoState(
            repo_url="https://forge.test/r",
            pinned_ref="old", latest_ref="new",
            default_branch="main",
        )],
    )
    es.status = "in_progress"
    esp = sd / "soma-pkg-init.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(
        emacs_version="29.1",
        entries_summary={"total": 1, "in_progress": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    entry_ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem="soma-pkg-init",
        results=[{
            "init_file": "soma-pkg-init.el",
            "repos": [{"repo_url": "https://forge.test/r",
                        "pinned_ref": "old"}],
        }],
        xclip_checker=lambda: False,
        run_fn=make_fake_git(checkout_ok=True),
    )
    return RepoContext(
        entry_ctx=entry_ctx, repo_state=es.repos[0],
        temp_dir=td, clone_dir=td / "soma-pkg-init",
    )


def test_version_check_upgrade_required(tmp_path: Path) -> None:
    """Version check detects newer Emacs requirement."""
    repo_ctx = _ctx(tmp_path)
    repo_ctx.repo_state.min_emacs_version = "30.1"
    repo_ctx.entry_ctx.global_state.emacs_version = "29.1"
    task_version_check(repo_ctx)
    assert repo_ctx.repo_state.emacs_upgrade_required is True


def test_version_check_no_upgrade(tmp_path: Path) -> None:
    """Version check passes when Emacs is sufficient."""
    repo_ctx = _ctx(tmp_path)
    repo_ctx.repo_state.min_emacs_version = "28.1"
    repo_ctx.entry_ctx.global_state.emacs_version = "29.1"
    task_version_check(repo_ctx)
    assert repo_ctx.repo_state.emacs_upgrade_required is False
