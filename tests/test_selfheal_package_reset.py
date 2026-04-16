"""Tests for reset_entry_for_reprocessing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from selfheal_test_helpers import make_selfheal_ctx

from soma_inits_upgrades.selfheal_package_name import (
    reset_entry_for_reprocessing,
)
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_reset_full_structural_reset(tmp_path: Path) -> None:
    """Reset removes derived, clears tasks/fields, persists state."""
    ctx = make_selfheal_ctx(tmp_path, "soma-ivy-init.el", ["ivy", "swiper"])
    repo = ctx.entry_state.repos[0]
    repo.package_name = "wrong"
    repo.depends_on = ["dep1"]
    repo.min_emacs_version = "25.1"
    for key in repo.tier1_tasks_completed:
        repo.tier1_tasks_completed[key] = True
    for key in ctx.entry_state.tasks_completed:
        ctx.entry_state.tasks_completed[key] = True
    ctx.entry_state.multi_package_verified = True
    derived = RepoState(
        repo_url="https://forge.test/r", pinned_ref="a",
        package_name="swiper", is_monorepo_derived=True,
    )
    ctx.entry_state.repos.append(derived)

    reset_entry_for_reprocessing(ctx.entry_state, ctx.entry_state_path, "test reset reason")

    assert len(ctx.entry_state.repos) == 1
    r = ctx.entry_state.repos[0]
    assert not r.is_monorepo_derived
    assert r.package_name is None
    assert r.depends_on is None
    assert r.min_emacs_version is None
    assert not any(r.tier1_tasks_completed.values())
    assert not any(ctx.entry_state.tasks_completed.values())
    assert ctx.entry_state.multi_package_verified is False


def test_reset_preserves_done_reason_repos(tmp_path: Path) -> None:
    """Repos with done_reason set are preserved and not reset."""
    ctx = make_selfheal_ctx(tmp_path, "soma-evil-init.el", ["evil"])
    skipped = ctx.entry_state.repos[0]
    skipped.package_name = "evil-helpers"
    skipped.done_reason = "already_latest"
    for key in skipped.tier1_tasks_completed:
        skipped.tier1_tasks_completed[key] = True
    active = RepoState(
        repo_url="https://forge.test/r2", pinned_ref="b",
        package_name="evil-wrong",
    )
    for key in active.tier1_tasks_completed:
        active.tier1_tasks_completed[key] = True
    ctx.entry_state.repos.append(active)

    reset_entry_for_reprocessing(ctx.entry_state, ctx.entry_state_path, "mismatch")

    assert len(ctx.entry_state.repos) == 2
    assert ctx.entry_state.repos[0].package_name == "evil-helpers"
    assert all(ctx.entry_state.repos[0].tier1_tasks_completed.values())
    assert ctx.entry_state.repos[1].package_name is None
    assert not any(ctx.entry_state.repos[1].tier1_tasks_completed.values())


def test_reset_persists_state(tmp_path: Path) -> None:
    """State file on disk reflects the reset."""
    ctx = make_selfheal_ctx(tmp_path, "soma-dash-init.el", ["dash"])
    ctx.entry_state.repos[0].package_name = "wrong"
    for key in ctx.entry_state.repos[0].tier1_tasks_completed:
        ctx.entry_state.repos[0].tier1_tasks_completed[key] = True

    reset_entry_for_reprocessing(ctx.entry_state, ctx.entry_state_path, "persist test")

    from soma_inits_upgrades.state import read_entry_state
    reloaded = read_entry_state(ctx.entry_state_path)
    assert reloaded is not None
    assert reloaded.repos[0].package_name is None
    assert reloaded.multi_package_verified is False
