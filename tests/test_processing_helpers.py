"""Tests for processing_helpers.py: error/done, progress guard, self-healing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.processing_helpers import (
    set_entry_done_early,
    set_entry_error,
)
from soma_inits_upgrades.protocols import EntryContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(tmp_path: Path) -> EntryContext:
    """Build an EntryContext for helper tests."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
    )
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    return EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem="x",
        results=[], xclip_checker=lambda: False, run_fn=make_fake_git(),
    )


def test_set_entry_error(tmp_path: Path) -> None:
    """Error bookkeeping sets status, notes, and updates counters."""
    ctx = _ctx(tmp_path)
    set_entry_error(ctx, "test error")
    assert ctx.entry_state.status == "error"
    assert ctx.entry_state.notes == "test error"
    assert ctx.global_state.entries_summary.error == 1
    assert ctx.global_state.entries_summary.in_progress == 0


def test_set_entry_done_early(tmp_path: Path) -> None:
    """Done-early sets status and reason without changing counters."""
    ctx = _ctx(tmp_path)
    orig_in_progress = ctx.global_state.entries_summary.in_progress
    set_entry_done_early(ctx, "skipped", "user skipped")
    assert ctx.entry_state.status == "done"
    assert ctx.entry_state.done_reason == "skipped"
    assert ctx.global_state.entries_summary.in_progress == orig_in_progress

