"""Integration tests for entry processing dispatch: retry, changes, orphans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.phase_dispatch_run import dispatch_entry_processing
from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_schema import TASK_ORDER, EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path


def _done_tasks() -> dict[str, bool]:
    """Return tasks_completed with all tasks True."""
    return dict.fromkeys(TASK_ORDER, True)


def _setup_done_entry(
    sd: Path, name: str, tmp_path: Path,
) -> EntryState:
    """Create a fully-done entry state file."""
    es = EntryState(
        init_file=name,
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        status="done", tasks_completed=_done_tasks(),
    )
    atomic_write_json(sd / f"{name}.json", es)
    return es


def _gs(names: list[str], phase: str = "done") -> GlobalState:
    """Create a GlobalState with entry_processing at phase."""
    done = len(names) if phase == "done" else 0
    return GlobalState(
        entry_names=names, emacs_version="29.1",
        phases={"setup": "done", "entry_processing": phase},
        entries_summary={"total": len(names), "done": done},
    )


def test_retry_in_progress(tmp_path: Path) -> None:
    """Errored entry with retries is retried during in_progress."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        status="error", retries_remaining=3,
        tasks_completed={**dict.fromkeys(TASK_ORDER, False),
                         "clone": True, "default_branch": True},
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = _gs(["x.el"], phase="in_progress")
    gs.entries_summary.done = 0
    gs.entries_summary.error = 1
    atomic_write_json(sd / "global.json", gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"}]
    dispatch_entry_processing(results, sd, tmp_path, gs, make_fake_git(clone_ok=False))
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.retries_remaining == 2


def test_retry_done_phase(tmp_path: Path) -> None:
    """Errored entry retried when entry_processing is done."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        status="error", retries_remaining=3,
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = _gs(["x.el"])
    gs.entries_summary.done = 0
    gs.entries_summary.error = 1
    atomic_write_json(sd / "global.json", gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    results = [{"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"}]
    dispatch_entry_processing(results, sd, tmp_path, gs, make_fake_git(clone_ok=False))
    state = read_entry_state(sd / "x.el.json")
    assert state is not None and state.retries_remaining == 2


def test_retry_exhaustion(tmp_path: Path) -> None:
    """Exhausted retries skip the entry."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    _setup_done_entry(sd, "good.el", tmp_path)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
        status="error", retries_remaining=0,
    )
    atomic_write_json(sd / "x.el.json", es)
    gs = _gs(["good.el", "x.el"])
    gs.entries_summary.done = 1
    gs.entries_summary.error = 1
    atomic_write_json(sd / "global.json", gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    results = [
        {"init_file": "good.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"},
        {"init_file": "x.el", "repo_url": "https://forge.test/r", "pinned_ref": "a"},
    ]
    dispatch_entry_processing(results, sd, tmp_path, gs, make_fake_git())
    state = read_entry_state(sd / "x.el.json")
    assert state is not None and state.status == "error"
