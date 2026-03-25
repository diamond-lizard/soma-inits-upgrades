"""Integration tests for Per-Entry Processing stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.processing import process_single_entry
from soma_inits_upgrades.state import atomic_write_json, read_entry_state
from soma_inits_upgrades.state_schema import EntryState, GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def _setup(
    tmp_path: Path, **git_kw: object,
) -> tuple[dict[str, str], GlobalState, Path, Path]:
    """Set up dirs, state files, and return (entry, gs, sd, gsp)."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    entry = {"init_file": "x.el", "repo_url": "https://x.com/r", "pinned_ref": "old"}
    es = EntryState(init_file="x.el", repo_url="https://x.com/r", pinned_ref="old")
    atomic_write_json(sd / "x.el.json", es)
    gs = GlobalState(
        entry_names=["x.el"], emacs_version="29.1",
        entries_summary={"total": 1, "pending": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    gp = tmp_path / "soma-inits-dependency-graphs.json"
    write_graph(gp, {})
    return entry, gs, sd, gsp


def _pre_create_llm_outputs(tmp_path: Path, name: str) -> None:
    """Pre-create LLM output files so pauses succeed."""
    (tmp_path / f"{name}-security-review.md").write_text(
        "# Review\nRisk Rating: low\n", encoding="utf-8",
    )
    td = tmp_path / ".tmp"
    (td / f"{name.removesuffix('.el')}-upgrade-analysis.json").write_text(
        '{"change_summary": "ok"}', encoding="utf-8",
    )
    (tmp_path / f"{name}-upgrade-process.md").write_text(
        "# Summary of Changes\n## Breaking Changes\n## New Dependencies\n",
        encoding="utf-8",
    )


def test_happy_path(tmp_path: Path) -> None:
    """Full entry flows through all tasks to done."""
    entry, gs, sd, gsp = _setup(tmp_path)
    _pre_create_llm_outputs(tmp_path, "x.el")
    fg = make_fake_git()
    results = [entry]
    process_single_entry(
        entry, 1, 1, sd, tmp_path, gs, gsp,
        fg, results, lambda: False, input_fn=lambda _: "c",
    )
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.status == "done"
    ops = [op[0] for op in fg.operations]
    assert ops.index("clone") < ops.index("symbolic-ref")
    assert ops.index("symbolic-ref") < ops.index("rev-parse")


def test_clone_failure(tmp_path: Path) -> None:
    """Clone failure sets error status."""
    entry, gs, sd, gsp = _setup(tmp_path)
    fg = make_fake_git(clone_ok=False)
    process_single_entry(
        entry, 1, 1, sd, tmp_path, gs, gsp,
        fg, [entry], lambda: False,
    )
    state = read_entry_state(sd / "x.el.json")
    assert state is not None and state.status == "error"


def test_empty_diff_early_exit(tmp_path: Path) -> None:
    """Empty diff marks entry done immediately."""
    entry, gs, sd, gsp = _setup(tmp_path)
    fg = make_fake_git(diff_output="")
    process_single_entry(
        entry, 1, 1, sd, tmp_path, gs, gsp,
        fg, [entry], lambda: False,
    )
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.status == "done"
    assert state.done_reason == "empty_diff"


def test_progress_guard(tmp_path: Path) -> None:
    """Stuck iteration sets error."""
    from soma_inits_upgrades.processing import TASK_HANDLERS

    entry, gs, sd, gsp = _setup(tmp_path)
    es = read_entry_state(sd / "x.el.json")
    assert es is not None
    es.status = "in_progress"
    atomic_write_json(sd / "x.el.json", es)
    gs.entries_summary.pending = 0
    gs.entries_summary.in_progress = 1
    atomic_write_json(gsp, gs)
    def noop(ctx: object) -> bool:
        return False
    orig = TASK_HANDLERS["clone"]
    TASK_HANDLERS["clone"] = noop  # type: ignore[assignment]
    try:
        process_single_entry(
            entry, 1, 1, sd, tmp_path, gs, gsp,
            make_fake_git(), [entry], lambda: False,
        )
        state = read_entry_state(sd / "x.el.json")
        assert state is not None and state.status == "error"
        assert "no progress" in (state.notes or "")
    finally:
        TASK_HANDLERS["clone"] = orig
