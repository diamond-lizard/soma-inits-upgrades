"""E2E test: Bug 1 — package name mismatch self-heal."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from e2e_bug_helpers import (
    deps_handler_that_sets_name,
    mark_all_tier1_done,
    tier2_noop_handler,
)
from monorepo_test_helpers import make_init_file
from runner_helpers import make_ctx
from runner_patch_helpers import (
    PATCH_CC,
    PATCH_T2,
    PATCH_TC,
    noop_clone_cleanup,
    ok_tier1,
)

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

_URL = "https://forge.test/r"
_T1_PATCH = "soma_inits_upgrades.processing.TIER_1_HANDLERS"


def test_wrong_name_is_corrected(tmp_path: Path) -> None:
    """Package name 'dash-functional' is corrected to 'dash'."""
    repo = RepoState(repo_url=_URL, pinned_ref="a")
    repo.package_name = "dash-functional"
    mark_all_tier1_done(repo)
    ctx = make_ctx(tmp_path, [repo])
    for key in ctx.entry_state.tasks_completed:
        ctx.entry_state.tasks_completed[key] = True
    inits_dir = tmp_path / "inits"
    make_init_file(inits_dir, "x.el", ["dash"])
    ctx.inits_dir = inits_dir
    repo_dir = ctx.tmp_dir / derive_repo_dir_name(_URL)
    repo_dir.mkdir(parents=True)
    atomic_write_json(ctx.entry_state_path, ctx.entry_state)
    log: list[str] = []
    t1 = {t: ok_tier1(log, t) for t in TIER_1_TASKS}
    t1["deps"] = deps_handler_that_sets_name("dash", log)
    t2 = {t: tier2_noop_handler(log, t) for t in TIER_2_TASKS}
    with (
        patch(_T1_PATCH, t1),
        patch(PATCH_T2, t2),
        patch(PATCH_CC, noop_clone_cleanup),
        patch(PATCH_TC, lambda ctx: False),
    ):
        run_entry_task_loop(ctx)
    assert ctx.entry_state.repos[0].package_name == "dash"
