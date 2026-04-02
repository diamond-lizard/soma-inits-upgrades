"""Tests for monorepo package disambiguation in task_deps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from test_entry_tasks_analysis import _ctx

from soma_inits_upgrades.entry_tasks_analysis import task_deps

if TYPE_CHECKING:
    from pathlib import Path


def test_deps_monorepo_selects_user_choice(tmp_path: Path) -> None:
    """Deps task uses input_fn for monorepo package disambiguation."""
    repo_ctx = _ctx(tmp_path, input_fn=lambda prompt: "2")
    repo_ctx.clone_dir.mkdir()
    (repo_ctx.clone_dir / "alpha.el").write_text(
        ';; Package-Requires: ((emacs "27.1") (dash "2.19"))\n',
        encoding="utf-8",
    )
    (repo_ctx.clone_dir / "beta.el").write_text(
        ';; Package-Requires: ((emacs "28.1") (magit "3.0"))\n',
        encoding="utf-8",
    )
    repo_ctx.repo_state.tier1_tasks_completed["clone"] = True
    task_deps(repo_ctx)
    assert repo_ctx.repo_state.package_name == "beta"
    assert "magit" in (repo_ctx.repo_state.depends_on or [])
    assert repo_ctx.repo_state.min_emacs_version == "28.1"
