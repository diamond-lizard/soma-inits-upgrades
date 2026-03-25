"""Tests for processing.py: find_next_task, loop exceptions, handler validation."""

from __future__ import annotations

import pytest

from soma_inits_upgrades.processing import find_next_task
from soma_inits_upgrades.state_schema import TASK_ORDER


def _tasks(done_keys: list[str]) -> dict[str, bool]:
    """Build a tasks_completed dict with specified keys marked True."""
    return {k: k in done_keys for k in TASK_ORDER}


def test_find_next_task_some_done() -> None:
    """First incomplete task is returned when some are done."""
    tasks = _tasks(["clone", "default_branch"])
    assert find_next_task(tasks) == "latest_ref"


def test_find_next_task_all_done() -> None:
    """Returns None when all tasks are complete."""
    tasks = _tasks(list(TASK_ORDER))
    assert find_next_task(tasks) is None


def test_find_next_task_none_done() -> None:
    """Returns the first task when none are done."""
    tasks = _tasks([])
    assert find_next_task(tasks) == "clone"


def test_find_next_task_gap_in_middle() -> None:
    """Identifies a gap when middle tasks are incomplete."""
    done = ["clone", "default_branch", "latest_ref", "deps"]
    tasks = _tasks(done)
    assert find_next_task(tasks) == "diff"


def test_run_entry_task_loop_exception(tmp_path: object) -> None:
    """Handler RuntimeError sets entry to error status."""
    from pathlib import Path

    from fakes import make_fake_git

    from soma_inits_upgrades.processing import TASK_HANDLERS, run_entry_task_loop
    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_schema import EntryState, GlobalState
    p = Path(str(tmp_path))
    sd = p / ".state"
    sd.mkdir(parents=True)
    td = p / ".tmp"
    td.mkdir()
    es = EntryState(init_file="x.el", repo_url="https://x.com/r", pinned_ref="a")
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)

    def boom(ctx: object) -> bool:
        raise RuntimeError("test boom")

    orig = TASK_HANDLERS["clone"]
    TASK_HANDLERS["clone"] = boom  # type: ignore[assignment]
    try:
        ctx = EntryContext(
            entry_state=es, entry_state_path=esp,
            global_state=gs, global_state_path=gsp,
            entry_idx=1, total=1, output_dir=p, tmp_dir=td,
            state_dir=sd, init_stem="x",
            results=[{"init_file": "x.el", "repo_url": "https://x.com/r", "pinned_ref": "a"}],
            xclip_checker=lambda: False, run_fn=make_fake_git(),
        )
        run_entry_task_loop(ctx)
        assert es.status == "error"
        assert "test boom" in (es.notes or "")
    finally:
        TASK_HANDLERS["clone"] = orig


def test_run_entry_task_loop_keyboard_interrupt(tmp_path: object) -> None:
    """KeyboardInterrupt propagates without being caught."""
    from pathlib import Path

    from fakes import make_fake_git

    from soma_inits_upgrades.processing import TASK_HANDLERS, run_entry_task_loop
    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_schema import EntryState, GlobalState
    p = Path(str(tmp_path))
    sd = p / ".state"
    sd.mkdir(parents=True)
    td = p / ".tmp"
    td.mkdir()
    es = EntryState(init_file="x.el", repo_url="https://x.com/r", pinned_ref="a")
    es.status = "in_progress"
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)

    def interrupt(ctx: object) -> bool:
        raise KeyboardInterrupt

    orig = TASK_HANDLERS["clone"]
    TASK_HANDLERS["clone"] = interrupt  # type: ignore[assignment]
    try:
        ctx = EntryContext(
            entry_state=es, entry_state_path=esp,
            global_state=gs, global_state_path=gsp,
            entry_idx=1, total=1, output_dir=p, tmp_dir=td,
            state_dir=sd, init_stem="x",
            results=[{"init_file": "x.el", "repo_url": "https://x.com/r", "pinned_ref": "a"}],
            xclip_checker=lambda: False, run_fn=make_fake_git(),
        )
        with pytest.raises(KeyboardInterrupt):
            run_entry_task_loop(ctx)
    finally:
        TASK_HANDLERS["clone"] = orig


def test_validate_handlers_missing_key() -> None:
    """ValueError raised when TASK_HANDLERS misses a TASK_ORDER key."""
    from soma_inits_upgrades.processing import TASK_HANDLERS, _validate_handlers

    orig = TASK_HANDLERS.pop("clone")
    try:
        with pytest.raises(ValueError, match=r"Missing handlers.*clone"):
            _validate_handlers()
    finally:
        TASK_HANDLERS["clone"] = orig


def test_validate_handlers_extra_key() -> None:
    """ValueError raised when TASK_HANDLERS has extra key."""
    from soma_inits_upgrades.processing import TASK_HANDLERS, _validate_handlers

    TASK_HANDLERS["bogus"] = lambda ctx: False  # type: ignore[assignment]
    try:
        with pytest.raises(ValueError, match=r"Extra handlers.*bogus"):
            _validate_handlers()
    finally:
        del TASK_HANDLERS["bogus"]
