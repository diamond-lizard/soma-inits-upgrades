"""Integration tests for entry change detection during Setup."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.phase_orchestration import run_setup
from soma_inits_upgrades.state_schema import GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def _write_input(tmp: Path, entries: list[dict[str, str]]) -> Path:
    """Write a stale inits JSON file and return its path."""
    data = {"results": entries}
    p = tmp / "stale.json"
    p.write_text(json.dumps(data))
    return p


def _setup_and_force_rerun(
    tmp_path: Path, entries: list[dict[str, str]],
) -> tuple[Path, Path]:
    """Run initial setup and force setup re-run by resetting phase."""
    inp = _write_input(tmp_path, entries)
    out = tmp_path / "out"
    state_dir = out / ".state"
    state_dir.mkdir(parents=True)
    results = json.loads(inp.read_text())["results"]
    gs_path = state_dir / "global.json"
    pre_gs = GlobalState(emacs_version="29.1")

    gs = run_setup(pre_gs, gs_path, inp.resolve(), out, state_dir, results)
    assert gs.phases.setup == "done"

    # Force setup re-run by resetting phase
    gs.phases.setup = "pending"
    from soma_inits_upgrades.state import atomic_write_json
    atomic_write_json(gs_path, gs)
    return inp, out


def test_repo_url_change_resets_entry(tmp_path: Path) -> None:
    """Changing repo_url resets the per-entry state file."""
    entries = [{"init_file": "a.el",
                "repo_url": "https://github.com/old/repo",
                "pinned_ref": "abc123"}]
    inp, out = _setup_and_force_rerun(tmp_path, entries)
    new_entries = [{"init_file": "a.el",
                    "repo_url": "https://github.com/new/repo",
                    "pinned_ref": "abc123"}]
    inp = _write_input(tmp_path, new_entries)
    state_dir = out / ".state"
    gs_path = state_dir / "global.json"

    from soma_inits_upgrades.state import read_global_state
    gs = read_global_state(gs_path)
    results = json.loads(inp.read_text())["results"]
    run_setup(gs, gs_path, inp.resolve(), out, state_dir, results)

    es = json.loads((state_dir / "a.el.json").read_text())
    assert es["repo_url"] == "https://github.com/new/repo"


def test_pinned_ref_change_resets_entry(tmp_path: Path) -> None:
    """Changing pinned_ref resets the per-entry state file."""
    entries = [{"init_file": "a.el",
                "repo_url": "https://github.com/x/y",
                "pinned_ref": "old111"}]
    inp, out = _setup_and_force_rerun(tmp_path, entries)
    new_entries = [{"init_file": "a.el",
                    "repo_url": "https://github.com/x/y",
                    "pinned_ref": "new222"}]
    inp = _write_input(tmp_path, new_entries)
    state_dir = out / ".state"
    gs_path = state_dir / "global.json"

    from soma_inits_upgrades.state import read_global_state
    gs = read_global_state(gs_path)
    results = json.loads(inp.read_text())["results"]
    run_setup(gs, gs_path, inp.resolve(), out, state_dir, results)

    es = json.loads((state_dir / "a.el.json").read_text())
    assert es["pinned_ref"] == "new222"
