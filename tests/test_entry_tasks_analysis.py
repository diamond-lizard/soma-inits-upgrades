"""Tests for entry_tasks_analysis.py: LLM and dependency task handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.entry_tasks_analysis import task_deps, task_version_check
from soma_inits_upgrades.protocols import EntryContext, RepoContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(
    tmp_path: Path, input_fn: object = None, **git_kw: object,
) -> RepoContext:
    """Build a RepoContext for analysis task tests."""
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
            "repo_url": "https://forge.test/r",
            "pinned_ref": "old",
        }],
        xclip_checker=lambda: False,
        run_fn=make_fake_git(checkout_ok=True, **git_kw),
        input_fn=input_fn,
    )
    return RepoContext(
        entry_ctx=entry_ctx, repo_state=es.repos[0],
        temp_dir=td, clone_dir=td / "soma-pkg-init",
    )


def test_deps_no_metadata(tmp_path: Path) -> None:
    """Deps task completes with empty deps when no metadata found."""
    repo_ctx = _ctx(tmp_path)
    repo_ctx.clone_dir.mkdir()
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    assert repo_ctx.repo_state.tier1_tasks_completed["deps"] is True
    assert repo_ctx.repo_state.depends_on == []
    assert repo_ctx.repo_state.package_name == "pkg"


def test_deps_with_pkg_el(tmp_path: Path) -> None:
    """Deps task extracts dependencies from a -pkg.el file."""
    repo_ctx = _ctx(tmp_path)
    repo_ctx.clone_dir.mkdir()
    pkg_el = repo_ctx.clone_dir / "pkg-pkg.el"
    pkg_el.write_text(
        '(define-package "pkg" "1.0" "desc" \'((emacs "27.1") (dash "2.19")))',
        encoding="utf-8",
    )
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    assert repo_ctx.repo_state.tier1_tasks_completed["deps"] is True
    assert "dash" in (repo_ctx.repo_state.depends_on or [])
    assert repo_ctx.repo_state.min_emacs_version == "27.1"
    assert repo_ctx.repo_state.package_name == "pkg"


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
