"""Tests for processing.py: tier finders, loop exceptions, handler validation."""

from __future__ import annotations

import pytest

from soma_inits_upgrades.processing import find_next_tier1_task, find_next_tier2_task
from soma_inits_upgrades.state_schema import TIER_1_TASKS, TIER_2_TASKS


def _tier1(done_keys: list[str]) -> dict[str, bool]:
    """Build a tier1_tasks_completed dict with specified keys marked True."""
    return {k: k in done_keys for k in TIER_1_TASKS}


def _tier2(done_keys: list[str]) -> dict[str, bool]:
    """Build a tasks_completed dict with specified keys marked True."""
    return {k: k in done_keys for k in TIER_2_TASKS}


def test_find_next_tier1_some_done() -> None:
    """First incomplete Tier 1 task is returned when some are done."""
    tasks = _tier1(["clone", "default_branch"])
    assert find_next_tier1_task(tasks) == "latest_ref"


def test_find_next_tier1_all_done() -> None:
    """Returns None when all Tier 1 tasks are complete."""
    tasks = _tier1(list(TIER_1_TASKS))
    assert find_next_tier1_task(tasks) is None


def test_find_next_tier1_none_done() -> None:
    """Returns the first Tier 1 task when none are done."""
    tasks = _tier1([])
    assert find_next_tier1_task(tasks) == "clone"


def test_find_next_tier2_some_done() -> None:
    """First incomplete Tier 2 task is returned when some are done."""
    tasks = _tier2(["security_review"])
    assert find_next_tier2_task(tasks) == "upgrade_analysis"


def test_find_next_tier2_all_done() -> None:
    """Returns None when all Tier 2 tasks are complete."""
    tasks = _tier2(list(TIER_2_TASKS))
    assert find_next_tier2_task(tasks) is None


def test_run_entry_task_loop_exception(tmp_path: object) -> None:
    """Handler RuntimeError sets repo to error via set_repo_error."""
    from pathlib import Path

    from fakes import make_fake_git

    from soma_inits_upgrades.processing import TIER_1_HANDLERS, run_entry_task_loop
    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState
    p = Path(str(tmp_path))
    sd = p / ".state"
    sd.mkdir(parents=True)
    td = p / ".tmp"
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

    def boom(ctx: object) -> bool:
        raise RuntimeError("test boom")

    orig = TIER_1_HANDLERS["clone"]
    TIER_1_HANDLERS["clone"] = boom  # type: ignore[assignment]
    try:
        ctx = EntryContext(
            entry_state=es, entry_state_path=esp,
            global_state=gs, global_state_path=gsp,
            entry_idx=1, total=1, output_dir=p, tmp_dir=td,
            state_dir=sd, init_stem="x",
            results=[{
                "init_file": "x.el",
                "repos": [{"repo_url": "https://forge.test/r", "pinned_ref": "a"}],
            }],
            xclip_checker=lambda: False, run_fn=make_fake_git(),
        )
        run_entry_task_loop(ctx)
        assert es.repos[0].done_reason == "error"
        assert "test boom" in (es.repos[0].notes or "")
    finally:
        TIER_1_HANDLERS["clone"] = orig


def test_run_entry_task_loop_keyboard_interrupt(tmp_path: object) -> None:
    """KeyboardInterrupt propagates without being caught."""
    from pathlib import Path

    from fakes import make_fake_git

    from soma_inits_upgrades.processing import TIER_1_HANDLERS, run_entry_task_loop
    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState
    p = Path(str(tmp_path))
    sd = p / ".state"
    sd.mkdir(parents=True)
    td = p / ".tmp"
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

    def interrupt(ctx: object) -> bool:
        raise KeyboardInterrupt

    orig = TIER_1_HANDLERS["clone"]
    TIER_1_HANDLERS["clone"] = interrupt  # type: ignore[assignment]
    try:
        ctx = EntryContext(
            entry_state=es, entry_state_path=esp,
            global_state=gs, global_state_path=gsp,
            entry_idx=1, total=1, output_dir=p, tmp_dir=td,
            state_dir=sd, init_stem="x",
            results=[{
                "init_file": "x.el",
                "repos": [{"repo_url": "https://forge.test/r", "pinned_ref": "a"}],
            }],
            xclip_checker=lambda: False, run_fn=make_fake_git(),
        )
        with pytest.raises(KeyboardInterrupt):
            run_entry_task_loop(ctx)
    finally:
        TIER_1_HANDLERS["clone"] = orig


def test_validate_handlers_missing_key() -> None:
    """ValueError raised when TIER_1_HANDLERS misses a task key."""
    from soma_inits_upgrades.processing import TIER_1_HANDLERS, _validate_handlers

    orig = TIER_1_HANDLERS.pop("clone")
    try:
        with pytest.raises(ValueError, match=r"Missing.*clone"):
            _validate_handlers()
    finally:
        TIER_1_HANDLERS["clone"] = orig


def test_validate_handlers_extra_key() -> None:
    """ValueError raised when TIER_2_HANDLERS has extra key."""
    from soma_inits_upgrades.processing import TIER_2_HANDLERS, _validate_handlers

    TIER_2_HANDLERS["bogus"] = lambda ctx: False  # type: ignore[assignment]
    try:
        with pytest.raises(ValueError, match=r"Extra.*bogus"):
            _validate_handlers()
    finally:
        del TIER_2_HANDLERS["bogus"]
