"""Integration test: progress guard in single entry processing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.processing import TIER_1_HANDLERS
from soma_inits_upgrades.processing_entry import process_single_entry
from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def test_progress_guard(tmp_path: Path) -> None:
    """Stuck iteration sets error."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    _url = "https://forge.test/r"
    entry = {
        "init_file": "x.el",
        "repos": [{"repo_url": _url, "pinned_ref": "old"}],
    }
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="old",
        )],
    )
    es.status = "in_progress"
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(
        entry_names=["x.el"], emacs_version="29.1",
        entries_summary={"total": 1, "in_progress": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})

    def noop(ctx: object) -> bool:
        return False

    orig = TIER_1_HANDLERS["clone"]
    TIER_1_HANDLERS["clone"] = noop  # type: ignore[assignment]
    try:
        process_single_entry(
            entry, 1, 1, sd, tmp_path, gs, gsp,
            make_fake_git(), [entry], lambda: False,
        )
        state = read_entry_state(sd / "x.el.json")
        assert state is not None
        assert state.repos[0].done_reason == "error"
        assert "no progress" in (state.repos[0].notes or "")
    finally:
        TIER_1_HANDLERS["clone"] = orig


def test_empty_diff_early_exit(tmp_path: Path) -> None:
    """Empty diff marks entry done immediately."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    _url = "https://forge.test/r"
    entry = {
        "init_file": "x.el",
        "repos": [{"repo_url": _url, "pinned_ref": "old"}],
    }
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="old",
        )],
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(
        entry_names=["x.el"], emacs_version="29.1",
        entries_summary={"total": 1, "pending": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    fg = make_fake_git(diff_output="")
    process_single_entry(
        entry, 1, 1, sd, tmp_path, gs, gsp,
        fg, [entry], lambda: False,
    )
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.repos[0].done_reason == "empty_diff"
