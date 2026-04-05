"""Integration tests: self-healing and change detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.graph import read_graph, write_graph
from soma_inits_upgrades.phase_dispatch_run import dispatch_entry_processing
from soma_inits_upgrades.processing_entry import process_single_entry
from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_schema import TIER_2_TASKS, EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


_URL = "https://forge.test/r"


def _entry(name: str, ref: str) -> dict[str, object]:
    return {"init_file": name, "repos": [{"repo_url": _URL, "pinned_ref": ref}]}


def test_self_healing_reclone(tmp_path: Path) -> None:
    """Missing clone dir triggers self-healing re-clone."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="old",
        )],
    )
    es.status = "in_progress"
    es.tasks_completed["clone"] = True
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(
        entry_names=["x.el"], emacs_version="29.1",
        entries_summary={"total": 1, "in_progress": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    entry = _entry("x.el", "old")
    fg = make_fake_git(clone_ok=False)
    process_single_entry(
        entry, 1, 1, sd, tmp_path, gs, gsp, fg, [entry], lambda: False, input_fn=lambda _: "c",
    )
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    repo = state.repos[0]
    assert repo.tier1_tasks_completed["clone"] is False or repo.done_reason == "error"


def test_orphan_removal(tmp_path: Path) -> None:
    """Removed entry's state and graph data are cleaned up."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    for name in ("keep.el", "drop.el"):
        es = EntryState(
            init_file=name,
            repos=[RepoState(
                repo_url="https://forge.test/r",
                pinned_ref="a",
            )],
            status="done",
            tasks_completed=dict.fromkeys((*TIER_2_TASKS, "temp_cleanup"), True),
        )
        atomic_write_json(sd / f"{name}.json", es)
    gs = GlobalState(
        entry_names=["keep.el", "drop.el"], emacs_version="29.1",
        phases={"setup": "done", "entry_processing": "done"},
        entries_summary={"total": 2, "done": 2},
    )
    atomic_write_json(sd / "global.json", gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {
        "drop.el": {"packages": [
            {"package": "drop", "repo_url": "https://github.com/t/drop",
             "depends_on": [], "min_emacs_version": None},
        ], "depended_on_by": []},
    })
    results = [_entry("keep.el", "a")]
    dispatch_entry_processing(results, sd, tmp_path, gs, make_fake_git(), input_fn=lambda _: "c")
    assert "drop.el" not in gs.entry_names
    assert not (sd / "drop.el.json").exists()
    graph, _ = read_graph(tmp_path / "soma-inits-dependency-graphs.json")
    assert "drop.el" not in graph
