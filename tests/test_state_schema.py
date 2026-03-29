"""Tests for state_schema.py."""

from __future__ import annotations

from soma_inits_upgrades.state_schema import (
    TIER_2_TASKS,
    EntryState,
    GlobalState,
    RepoState,
)


def test_global_state_defaults() -> None:
    """Verify GlobalState() with no args has all expected defaults."""
    gs = GlobalState()
    assert gs.phases.setup == "pending"
    assert gs.phases.entry_processing == "pending"
    assert gs.phases.graph_finalization == "pending"
    assert gs.phases.summary == "pending"
    assert gs.completed is False
    assert gs.date_completed is None
    assert gs.entry_names == []
    assert gs.entries_summary.total == 0
    assert gs.current_entry is None


def test_entry_state_requires_fields() -> None:
    """Verify EntryState requires init_file, repo_url, pinned_ref."""
    state = EntryState(
        init_file="a.el",
        repos=[RepoState(
            repo_url="https://x/y", pinned_ref="abc",
        )],
    )
    assert state.status == "pending"
    assert state.repos[0].package_name is None
    assert state.repos[0].emacs_upgrade_required is False
    assert state.done_reason is None
    assert state.retries_remaining == 5


def test_tier2_keys_match_tasks_completed() -> None:
    """Verify Tier 2 + cleanup keys match default tasks_completed."""
    state = EntryState(
        init_file="a.el",
        repos=[RepoState(
            repo_url="https://x/y", pinned_ref="abc",
        )],
    )
    assert list(state.tasks_completed.keys()) == [*TIER_2_TASKS, "cleanup"]
    assert all(v is False for v in state.tasks_completed.values())


def test_entry_context_construction() -> None:
    """Verify EntryContext construction with all required fields."""
    from pathlib import Path

    from soma_inits_upgrades.protocols import EntryContext

    es = EntryState(
        init_file="a.el",
        repos=[RepoState(
            repo_url="https://x/y", pinned_ref="abc",
        )],
    )
    gs = GlobalState()
    ctx = EntryContext(
        entry_state=es,
        entry_state_path=Path("/tmp/e.json"),
        global_state=gs,
        global_state_path=Path("/tmp/g.json"),
        entry_idx=1,
        total=2,
        output_dir=Path("/tmp/out"),
        tmp_dir=Path("/tmp/out/.tmp"),
        state_dir=Path("/tmp/out/.state"),
        init_stem="a",
        results=[],
        xclip_checker=lambda: False,
        run_fn=lambda args, **kw: __import__("subprocess").CompletedProcess(args, 0),
    )
    assert ctx.entry_idx == 1
    assert ctx.reset_counters == {}
