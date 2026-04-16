"""Tests for monorepo multi-package detection in task_deps (Phase 400)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from monorepo_test_helpers import make_el_with_header, make_monorepo_ctx

from soma_inits_upgrades.entry_tasks_analysis import task_deps

if TYPE_CHECKING:
    from pathlib import Path


def test_three_packages_creates_derived_entries(tmp_path: Path) -> None:
    """Three use-package declarations produce 3 RepoStates, 2 derived."""
    repo_ctx = make_monorepo_ctx(
        tmp_path, "soma-ivy-init.el", ["ivy", "swiper", "counsel"],
    )
    repo_ctx.clone_dir.mkdir(parents=True)
    make_el_with_header(repo_ctx.clone_dir, "ivy", '((emacs "25.1"))')
    make_el_with_header(repo_ctx.clone_dir, "swiper", '((emacs "25.1") (ivy "0.13"))')
    make_el_with_header(repo_ctx.clone_dir, "counsel", '((emacs "25.1") (swiper "0.13"))')
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    repos = repo_ctx.entry_ctx.entry_state.repos
    assert len(repos) == 3
    names = {r.package_name for r in repos}
    assert names == {"ivy", "swiper", "counsel"}
    original = repos[0]
    assert original.is_monorepo_derived is False
    derived = [r for r in repos if r.is_monorepo_derived]
    assert len(derived) == 2
    for d in derived:
        assert all(d.tier1_tasks_completed.values())
    assert repo_ctx.entry_ctx.entry_state.multi_package_verified is True


def test_two_packages_with_extras(tmp_path: Path) -> None:
    """Two declared packages plus unrelated extras produce 2 RepoStates."""
    repo_ctx = make_monorepo_ctx(
        tmp_path, "soma-alpha-init.el", ["alpha", "beta"],
    )
    repo_ctx.clone_dir.mkdir(parents=True)
    make_el_with_header(repo_ctx.clone_dir, "alpha", '((emacs "27.1"))')
    make_el_with_header(repo_ctx.clone_dir, "beta", '((emacs "28.1") (dash "2.19"))')
    make_el_with_header(repo_ctx.clone_dir, "gamma", '((emacs "26.1"))')
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    repos = repo_ctx.entry_ctx.entry_state.repos
    assert len(repos) == 2
    names = {r.package_name for r in repos}
    assert names == {"alpha", "beta"}
    derived = [r for r in repos if r.is_monorepo_derived]
    assert len(derived) == 1


def test_single_package_no_extras(tmp_path: Path) -> None:
    """Single use-package with extra candidates creates no derived entries."""
    repo_ctx = make_monorepo_ctx(
        tmp_path, "soma-magit-init.el", ["magit"],
    )
    repo_ctx.clone_dir.mkdir(parents=True)
    make_el_with_header(repo_ctx.clone_dir, "magit", '((emacs "27.1"))')
    make_el_with_header(repo_ctx.clone_dir, "magit-section", '((emacs "26.1"))')
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    repos = repo_ctx.entry_ctx.entry_state.repos
    assert len(repos) == 1
    assert repos[0].package_name == "magit"
    assert repos[0].is_monorepo_derived is False
    assert repo_ctx.entry_ctx.entry_state.multi_package_verified is True
