"""Tests for processing_helpers.py: progress guard and self-healing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fakes import make_fake_git

from soma_inits_upgrades.processing_helpers import (
    check_progress,
    self_heal_resource,
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
        results=[], xclip_checker=lambda: False,
        run_fn=make_fake_git(),
    )


def test_check_progress_task_completed() -> None:
    """Progress detected when task count increased."""
    assert check_progress(2, {"a": True, "b": True, "c": True}, "in_progress")


def test_check_progress_self_healing() -> None:
    """Progress detected when task count decreased."""
    assert check_progress(3, {"a": True, "b": False}, "in_progress")


def test_check_progress_status_changed() -> None:
    """Progress detected when status is done/error."""
    assert check_progress(2, {"a": True, "b": True}, "done")
    assert check_progress(2, {"a": True, "b": True}, "error")


def test_check_progress_no_change() -> None:
    """No progress when nothing changed."""
    assert not check_progress(
        2, {"a": True, "b": True}, "in_progress",
    )


def test_self_heal_resource_exists(tmp_path: Path) -> None:
    """Returns False when resource exists."""
    ctx = _ctx(tmp_path)
    (tmp_path / "file.txt").write_text("data")
    assert self_heal_resource(
        tmp_path / "file.txt", "clone", ctx,
    ) is False


def test_self_heal_resource_missing_resets(tmp_path: Path) -> None:
    """Resets creating task when resource missing."""
    ctx = _ctx(tmp_path)
    ctx.entry_state.tasks_completed["clone"] = True
    result = self_heal_resource(tmp_path / "gone.txt", "clone", ctx)
    assert result is True
    assert ctx.entry_state.tasks_completed["clone"] is False
    assert ctx.reset_counters["clone"] == 1


def test_self_heal_limit_exceeded(tmp_path: Path) -> None:
    """Error set and SystemExit raised when self-healing limit reached."""
    ctx = _ctx(tmp_path)
    ctx.reset_counters["clone"] = 4
    ctx.entry_state.tasks_completed["clone"] = True
    with pytest.raises(SystemExit):
        self_heal_resource(tmp_path / "gone.txt", "clone", ctx)
    assert ctx.entry_state.status == "error"
    assert "self-healing limit" in (ctx.entry_state.notes or "")
