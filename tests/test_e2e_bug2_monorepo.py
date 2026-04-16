"""E2E test: Bug 2 — monorepo multi-package self-heal."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from e2e_bug_helpers import mark_all_tier1_done, tier2_noop_handler
from fakes import make_fake_git
from monorepo_test_helpers import make_el_with_header, make_init_file
from runner_helpers import make_ctx
from runner_patch_helpers import (
    PATCH_CC,
    PATCH_T2,
    PATCH_TC,
    noop_clone_cleanup,
    ok_tier1,
)

from soma_inits_upgrades.entry_tasks_analysis import task_deps
from soma_inits_upgrades.processing_runner import run_entry_task_loop
from soma_inits_upgrades.repo_utils import derive_repo_dir_name
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import (
    TIER_1_TASKS,
    TIER_2_TASKS,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path

_URL = "https://github.com/test/swiper"
_T1_PATCH = "soma_inits_upgrades.processing.TIER_1_HANDLERS"


def test_missing_packages_are_created(tmp_path: Path) -> None:
    """Monorepo with 3 packages creates derived entries."""
    repo = RepoState(
        repo_url=_URL, pinned_ref="a",
        latest_ref="b", default_branch="main",
        package_name="counsel",
    )
    mark_all_tier1_done(repo)
    ctx = make_ctx(tmp_path, [repo])
    ctx.entry_state.init_file = "soma-ivy-init.el"
    ctx.init_stem = "soma-ivy-init"
    for key in ctx.entry_state.tasks_completed:
        ctx.entry_state.tasks_completed[key] = True
    inits_dir = tmp_path / "inits"
    make_init_file(
        inits_dir, "soma-ivy-init.el",
        ["ivy", "swiper", "counsel"],
    )
    ctx.inits_dir = inits_dir
    ctx.run_fn = make_fake_git(checkout_ok=True)
    ctx.input_fn = lambda prompt: "1"
    clone_dir = (
        ctx.tmp_dir / derive_repo_dir_name(_URL) / "clone"
    )
    clone_dir.mkdir(parents=True)
    make_el_with_header(clone_dir, "ivy", '((emacs "25.1"))')
    make_el_with_header(
        clone_dir, "swiper", '((emacs "25.1") (ivy "0.13"))',
    )
    make_el_with_header(
        clone_dir, "counsel",
        '((emacs "25.1") (swiper "0.13"))',
    )
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t1["deps"] = task_deps
    t2 = {t: tier2_noop_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(_T1_PATCH, t1),
        patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, lambda ctx: False),
    ):
        run_entry_task_loop(ctx)
    repos = ctx.entry_state.repos
    assert len(repos) == 3
    names = {r.package_name for r in repos}
    assert names == {"ivy", "swiper", "counsel"}
    derived = [r for r in repos if r.is_monorepo_derived]
    assert len(derived) == 2
    assert ctx.entry_state.multi_package_verified is True
