"""Integration tests for Setup stage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _write_input(tmp: Path, entries: list[dict[str, str]] | None = None) -> Path:
    """Write a valid stale inits JSON file and return its path."""
    data = {"results": entries or [
        {"init_file": "soma-dash-init.el",
         "repo_url": "https://github.com/magnars/dash.el",
         "pinned_ref": "abc123"},
        {"init_file": "soma-magit-init.el",
         "repo_url": "https://github.com/magit/magit",
         "pinned_ref": "def456"},
    ]}
    p = tmp / "stale.json"
    p.write_text(json.dumps(data))
    return p


def test_fresh_setup_creates_all_artifacts(tmp_path: Path) -> None:
    """Fresh setup creates global state, per-entry states, dep graph, dirs."""
    from soma_inits_upgrades.phase_orchestration import run_setup
    from soma_inits_upgrades.state_schema import GlobalState

    inp = _write_input(tmp_path)
    out = tmp_path / "out"
    state_dir = out / ".state"
    state_dir.mkdir(parents=True)
    from soma_inits_upgrades.cli_helpers import load_stale_inits
    results = load_stale_inits(inp)
    gs_path = state_dir / "global.json"
    pre_gs = GlobalState(emacs_version="29.1")

    run_setup(pre_gs, gs_path, inp.resolve(), out, state_dir, results)

    assert (out / ".tmp").is_dir()
    assert gs_path.is_file()
    assert (state_dir / "soma-dash-init.el.json").is_file()
    assert (state_dir / "soma-magit-init.el.json").is_file()
    assert (out / "soma-inits-dependency-graphs.json").is_file()

    gs = json.loads(gs_path.read_text())
    assert gs["emacs_version"] == "29.1"
    assert gs["phases"]["setup"] == "done"
    assert gs["stale_inits_file"] == str(inp.resolve())
    assert len(gs["entry_names"]) == 2


def test_setup_skip_when_already_done(tmp_path: Path) -> None:
    """Setup is idempotent: running twice does not alter completed state."""
    from soma_inits_upgrades.phase_orchestration import run_setup
    from soma_inits_upgrades.state_schema import GlobalState

    inp = _write_input(tmp_path)
    out = tmp_path / "out"
    state_dir = out / ".state"
    state_dir.mkdir(parents=True)
    from soma_inits_upgrades.cli_helpers import load_stale_inits
    results = load_stale_inits(inp)
    gs_path = state_dir / "global.json"
    pre_gs = GlobalState(emacs_version="29.1")

    gs = run_setup(pre_gs, gs_path, inp.resolve(), out, state_dir, results)
    assert gs.phases.setup == "done"

    # Second run with completed state: setup functions are idempotent
    gs2 = run_setup(gs, gs_path, inp.resolve(), out, state_dir, results)
    assert gs2.phases.setup == "done"
    assert gs2.emacs_version == "29.1"

