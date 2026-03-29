"""Shared helpers for two-tier runner tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.protocols import EntryContext, RepoContext

if TYPE_CHECKING:
    from pathlib import Path
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import (
    EntryState,
    GlobalState,
    RepoState,
)


def make_ctx(tmp_path: Path, repos: list[RepoState]) -> EntryContext:
    """Build an EntryContext with the given repos and tmp dirs."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir(exist_ok=True)
    tmp_dir = tmp_path / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    es = EntryState(init_file="x.el", repos=repos)
    es_path = state_dir / "x.el.json"
    atomic_write_json(es_path, es)
    gs = GlobalState(
        emacs_version="29.1",
        entries_summary={"total": 1, "in_progress": 1},
    )
    gs_path = state_dir / "global.json"
    atomic_write_json(gs_path, gs)
    import subprocess as _sp
    return EntryContext(
        entry_state=es,
        entry_state_path=es_path,
        global_state=gs,
        global_state_path=gs_path,
        entry_idx=1, total=1,
        output_dir=tmp_path,
        tmp_dir=tmp_dir,
        state_dir=state_dir,
        init_stem="x",
        results=[],
        xclip_checker=lambda: False,
        run_fn=lambda args, **kw: _sp.CompletedProcess(args, 0),
    )


def tracking_handler(log: list[str], tag: str):
    """Return a handler that logs calls and marks the task complete."""
    def handler(ctx_or_repo: EntryContext | RepoContext) -> bool:
        log.append(tag)
        if isinstance(ctx_or_repo, RepoContext):
            repo = ctx_or_repo.repo_state
            if tag in repo.tier1_tasks_completed:
                repo.tier1_tasks_completed[tag] = True
        elif isinstance(ctx_or_repo, EntryContext):
            if tag in ctx_or_repo.entry_state.tasks_completed:
                ctx_or_repo.entry_state.tasks_completed[tag] = True
        return False
    return handler


def fake_cleanup(ctx: EntryContext) -> bool:
    """Fake cleanup handler that logs and marks complete."""
    ctx.entry_state.tasks_completed["cleanup"] = True
    return False
