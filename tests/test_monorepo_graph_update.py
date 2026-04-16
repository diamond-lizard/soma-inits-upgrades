"""Test that task_graph_update handles multiple RepoStates correctly."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from runner_helpers import make_ctx

from soma_inits_upgrades.entry_tasks_graph import task_graph_update
from soma_inits_upgrades.state_schema import RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_graph_update_produces_multi_package_entry(tmp_path: Path) -> None:
    """Graph update with 3 RepoStates produces a 3-element packages list."""
    repos = [
        RepoState(
            repo_url="https://github.com/abo-abo/swiper",
            pinned_ref="aaa", latest_ref="bbb", default_branch="main",
            package_name="ivy",
            depends_on=[],
            min_emacs_version="25.1",
        ),
        RepoState(
            repo_url="https://github.com/abo-abo/swiper",
            pinned_ref="aaa", latest_ref="bbb", default_branch="main",
            package_name="swiper",
            depends_on=["ivy"],
            min_emacs_version="25.1",
            is_monorepo_derived=True,
        ),
        RepoState(
            repo_url="https://github.com/abo-abo/swiper",
            pinned_ref="aaa", latest_ref="bbb", default_branch="main",
            package_name="counsel",
            depends_on=["swiper"],
            min_emacs_version="25.1",
            is_monorepo_derived=True,
        ),
    ]
    for r in repos:
        for k in r.tier1_tasks_completed:
            r.tier1_tasks_completed[k] = True
    ctx = make_ctx(tmp_path, repos)
    ctx.entry_state.init_file = "soma-ivy-counsel-and-swiper-init.el"
    ctx.init_stem = "soma-ivy-counsel-and-swiper-init"
    task_graph_update(ctx)
    graph_path = tmp_path / "soma-inits-dependency-graphs.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    entry = graph["soma-ivy-counsel-and-swiper-init.el"]
    pkgs = entry["packages"]
    assert len(pkgs) == 3
    names = {p["package"] for p in pkgs}
    assert names == {"ivy", "swiper", "counsel"}
    ivy_pkg = next(p for p in pkgs if p["package"] == "ivy")
    assert ivy_pkg["depends_on"] == []
    counsel_pkg = next(p for p in pkgs if p["package"] == "counsel")
    assert counsel_pkg["depends_on"] == ["swiper"]
