"""Tests for processing.py: task loop exception handling."""

from __future__ import annotations

from pathlib import Path

import pytest
from fakes import make_fake_git

from soma_inits_upgrades.processing import TIER_1_HANDLERS, run_entry_task_loop
from soma_inits_upgrades.protocols import EntryContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState


def _loop_ctx(tmp_path: Path) -> tuple[EntryState, EntryContext]:
    """Build an EntryContext for loop tests, return (es, ctx)."""
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
    gs = GlobalState(
        entries_summary={"total": 1, "in_progress": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=p, tmp_dir=td,
        state_dir=sd, init_stem="x",
        results=[{
            "init_file": "x.el",
            "repos": [{"repo_url": "https://forge.test/r",
                        "pinned_ref": "a"}],
        }],
        xclip_checker=lambda: False, run_fn=make_fake_git(),
    )
    return es, ctx


def test_run_entry_task_loop_exception(tmp_path: Path) -> None:
    """Handler RuntimeError sets repo to error via set_repo_error."""
    es, ctx = _loop_ctx(tmp_path)

    def boom(ctx: object) -> bool:
        raise RuntimeError("test boom")

    orig = TIER_1_HANDLERS["clone"]
    TIER_1_HANDLERS["clone"] = boom  # type: ignore[assignment]
    try:
        run_entry_task_loop(ctx)
        assert es.repos[0].done_reason == "error"
        assert "test boom" in (es.repos[0].notes or "")
    finally:
        TIER_1_HANDLERS["clone"] = orig


def test_run_entry_task_loop_keyboard_interrupt(
    tmp_path: Path,
) -> None:
    """KeyboardInterrupt propagates without being caught."""
    _es, ctx = _loop_ctx(tmp_path)

    def interrupt(ctx: object) -> bool:
        raise KeyboardInterrupt

    orig = TIER_1_HANDLERS["clone"]
    TIER_1_HANDLERS["clone"] = interrupt  # type: ignore[assignment]
    try:
        with pytest.raises(KeyboardInterrupt):
            run_entry_task_loop(ctx)
    finally:
        TIER_1_HANDLERS["clone"] = orig
