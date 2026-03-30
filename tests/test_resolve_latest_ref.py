"""Regression test: resolve_latest_ref must not double-prefix origin/."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_tasks_diff import resolve_latest_ref
from soma_inits_upgrades.git_ref_ops import detect_default_branch
from soma_inits_upgrades.protocols import EntryContext, RepoContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_resolve_latest_ref_uses_bare_branch(
    git_repo: dict, tmp_path: Path,
) -> None:
    """resolve_latest_ref must pass a bare branch name to rev_parse.

    rev_parse internally prepends origin/, so passing origin/{branch}
    results in the invalid ref origin/origin/{branch} and always fails.
    """
    clone = git_repo["clone"]
    branch = detect_default_branch(clone)
    assert branch is not None

    sd = tmp_path / "sd"
    sd.mkdir()
    repo = RepoState(
        repo_url="https://forge.test/r", pinned_ref="old",
    )
    repo.default_branch = branch
    es = EntryState(init_file="x.el", repos=[repo])
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path,
        tmp_dir=tmp_path / ".tmp", state_dir=sd, init_stem="x",
        results=[{"init_file": "x.el",
                  "repos": [{"repo_url": "https://forge.test/r",
                             "pinned_ref": "old"}]}],
        xclip_checker=lambda: False, run_fn=__import__("subprocess").run,
    )
    repo_ctx = RepoContext(
        entry_ctx=ctx, repo_state=repo,
        temp_dir=tmp_path / ".tmp", clone_dir=clone,
    )

    result = resolve_latest_ref(repo_ctx)
    assert result is not None, (
        "resolve_latest_ref returned None — likely double origin/ prefix"
    )
    assert len(result) == 40
    assert result == git_repo["sha2"]
