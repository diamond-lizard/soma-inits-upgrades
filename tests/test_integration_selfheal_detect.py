"""Integration tests: new and modified entry detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.phase_dispatch_run import dispatch_entry_processing
from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_schema import TIER_2_TASKS, EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

_URL = "https://forge.test/r"
_ALL_DONE = dict.fromkeys((*TIER_2_TASKS, "temp_cleanup"), True)


def _entry(name: str, ref: str) -> dict[str, object]:
    return {"init_file": name, "repos": [{"repo_url": _URL, "pinned_ref": ref}]}


def test_new_entry_detection(tmp_path: Path) -> None:
    """New entry added after all phases done is detected and processed."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    old_es = EntryState(
        init_file="old.el",
        repos=[RepoState(repo_url=_URL, pinned_ref="a")],
        status="done", tasks_completed=dict(_ALL_DONE),
    )
    atomic_write_json(sd / "old.el.json", old_es)
    gs = GlobalState(
        entry_names=["old.el"], emacs_version="29.1",
        phases={"setup": "done", "entry_processing": "done"},
        entries_summary={"total": 1, "done": 1},
    )
    atomic_write_json(sd / "global.json", gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    results = [_entry("old.el", "a"), _entry("new.el", "b")]
    dispatch_entry_processing(
        results, sd, tmp_path, gs, make_fake_git(clone_ok=False), input_fn=lambda _: "c",
    )
    assert "new.el" in gs.entry_names
    assert (sd / "new.el.json").exists()


def test_modified_entry_detection(tmp_path: Path) -> None:
    """Modified entry is reset and reprocessed."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(repo_url=_URL, pinned_ref="old")],
        status="done", tasks_completed=dict(_ALL_DONE),
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(
        entry_names=["x.el"], emacs_version="29.1",
        phases={"setup": "done", "entry_processing": "done"},
        entries_summary={"total": 1, "done": 1},
    )
    atomic_write_json(sd / "global.json", gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    results = [_entry("x.el", "NEW")]
    dispatch_entry_processing(
        results, sd, tmp_path, gs, make_fake_git(clone_ok=False), input_fn=lambda _: "c",
    )
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.repos[0].pinned_ref == "NEW"
