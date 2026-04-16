"""Tests for check_package_name_mismatch and check_multi_package_count."""

from __future__ import annotations

from typing import TYPE_CHECKING

from selfheal_test_helpers import make_selfheal_ctx

from soma_inits_upgrades.selfheal_package_name import (
    check_multi_package_count,
    check_package_name_mismatch,
)
from soma_inits_upgrades.state_schema import RepoState

_IVY_PKGS = ["ivy", "swiper", "counsel"]
if TYPE_CHECKING:
    from pathlib import Path


def test_correct_name_returns_none(tmp_path: Path) -> None:
    """Stored name matches declared name -> None."""
    ctx = make_selfheal_ctx(tmp_path, "soma-dash-init.el", ["dash"])
    ctx.entry_state.repos[0].package_name = "dash"
    assert check_package_name_mismatch(["dash"], ctx) is None


def test_wrong_name_returns_reason(tmp_path: Path) -> None:
    """Stored name differs from declared -> reason string."""
    ctx = make_selfheal_ctx(tmp_path, "soma-dash-init.el", ["dash"])
    ctx.entry_state.repos[0].package_name = "dash-functional"
    reason = check_package_name_mismatch(["dash"], ctx)
    assert reason is not None
    assert "dash-functional" in reason


def test_wrong_name_with_derived_entries(tmp_path: Path) -> None:
    """Mismatch detected even with monorepo-derived entries present."""
    ctx = make_selfheal_ctx(tmp_path, "soma-ivy-init.el", _IVY_PKGS)
    ctx.entry_state.repos[0].package_name = "wrong-pkg"
    derived = RepoState(
        repo_url="https://forge.test/r", pinned_ref="a",
        package_name="swiper", is_monorepo_derived=True,
    )
    ctx.entry_state.repos.append(derived)
    reason = check_package_name_mismatch(_IVY_PKGS, ctx)
    assert reason is not None
    assert "wrong-pkg" in reason


def test_all_none_names_returns_none(tmp_path: Path) -> None:
    """All repos have package_name=None -> None (deps not run yet)."""
    ctx = make_selfheal_ctx(tmp_path, "soma-dash-init.el", ["dash"])
    assert check_package_name_mismatch(["dash"], ctx) is None
    assert check_multi_package_count(["dash"], ctx) is None


def test_empty_declared_returns_none(tmp_path: Path) -> None:
    """Empty declared_names -> None from both detection functions."""
    ctx = make_selfheal_ctx(tmp_path, "soma-dash-init.el", ["dash"])
    ctx.entry_state.repos[0].package_name = "dash"
    assert check_package_name_mismatch([], ctx) is None
    assert check_multi_package_count([], ctx) is None


def test_done_reason_repo_excluded(tmp_path: Path) -> None:
    """Skipped repos (done_reason set) excluded from detection."""
    ctx = make_selfheal_ctx(tmp_path, "soma-evil-init.el", ["evil"])
    ctx.entry_state.repos[0].package_name = "evil-helpers"
    ctx.entry_state.repos[0].done_reason = "already_latest"
    active = RepoState(
        repo_url="https://forge.test/r2", pinned_ref="b",
        package_name="evil-helpers",
    )
    ctx.entry_state.repos.append(active)
    reason = check_package_name_mismatch(["evil"], ctx)
    assert reason is not None
    assert "evil-helpers" in reason


def test_multi_package_count_mismatch(tmp_path: Path) -> None:
    """Fewer repos than declarations -> reason string."""
    ctx = make_selfheal_ctx(tmp_path, "soma-ivy-init.el", _IVY_PKGS)
    ctx.entry_state.repos[0].package_name = "counsel"
    reason = check_multi_package_count(_IVY_PKGS, ctx)
    assert reason is not None
    assert "3" in reason


def test_multi_package_verified_skips(tmp_path: Path) -> None:
    """multi_package_verified=True -> None (already verified)."""
    ctx = make_selfheal_ctx(tmp_path, "soma-ivy-init.el", _IVY_PKGS)
    ctx.entry_state.repos[0].package_name = "counsel"
    ctx.entry_state.multi_package_verified = True
    assert check_multi_package_count(_IVY_PKGS, ctx) is None
