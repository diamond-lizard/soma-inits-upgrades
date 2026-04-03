"""Tests for entry_tasks_symbols.py: symbol task with search failure."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from fakes import make_fake_git

from soma_inits_upgrades.entry_tasks_symbols import task_symbols
from soma_inits_upgrades.protocols import EntryContext, RepoContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import (
    EntryState,
    GlobalState,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(tmp_path: Path) -> RepoContext:
    """Build a RepoContext with fake git and temp dirs."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True, exist_ok=True)
    td = tmp_path / ".tmp"
    td.mkdir(exist_ok=True)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="old",
        )],
    )
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    entry_ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem="x",
        results=[{
            "init_file": "x.el",
            "repos": [
                {"repo_url": "https://forge.test/r", "pinned_ref": "old"},
            ],
        }],
        xclip_checker=lambda: False, run_fn=make_fake_git(),
    )
    return RepoContext(
        entry_ctx=entry_ctx, repo_state=es.repos[0],
        temp_dir=td, clone_dir=td / "x",
    )


_EXTRACT = "soma_inits_upgrades.symbol_collection.extract_changed_symbols"
_SEARCH = "soma_inits_upgrades.symbols_io.search_symbol_usages"


def test_task_symbols_unverified_on_failure(tmp_path: Path) -> None:
    """Search failure writes _unverified_symbols to JSON."""
    repo_ctx = _ctx(tmp_path)
    diff_path = repo_ctx.temp_dir / "x.diff"
    diff_path.write_text("fake diff")
    syms = ["evil-mode", "dash-map"]
    with (
        patch(_EXTRACT, return_value=syms),
        patch(_SEARCH, return_value={}),
    ):
        task_symbols(repo_ctx)
    usage_path = repo_ctx.temp_dir / "x-usage-analysis.json"
    data = json.loads(usage_path.read_text(encoding="utf-8"))
    assert data["_unverified_symbols"] == ["evil-mode", "dash-map"]


def test_task_symbols_no_unverified_on_success(tmp_path: Path) -> None:
    """Successful search does not write _unverified_symbols."""
    repo_ctx = _ctx(tmp_path)
    diff_path = repo_ctx.temp_dir / "x.diff"
    diff_path.write_text("fake diff")
    success = {"evil-mode": [], "dash-map": ["init.el"]}
    with (
        patch(_EXTRACT, return_value=["evil-mode", "dash-map"]),
        patch(_SEARCH, return_value=success),
    ):
        task_symbols(repo_ctx)
    usage_path = repo_ctx.temp_dir / "x-usage-analysis.json"
    data = json.loads(usage_path.read_text(encoding="utf-8"))
    assert "_unverified_symbols" not in data
