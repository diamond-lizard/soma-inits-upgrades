"""Integration tests for Setup stage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from soma_inits_upgrades.main import cli

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
    inp = _write_input(tmp_path)
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result.exit_code == 0, result.output

    state_dir = out / ".state"
    assert state_dir.is_dir()
    assert (out / ".tmp").is_dir()
    assert (state_dir / "global.json").is_file()
    assert (state_dir / "soma-dash-init.el.json").is_file()
    assert (state_dir / "soma-magit-init.el.json").is_file()
    assert (out / "soma-inits-dependency-graphs.json").is_file()

    gs = json.loads((state_dir / "global.json").read_text())
    assert gs["emacs_version"] == "29.1"
    assert gs["phases"]["setup"] == "done"
    assert gs["stale_inits_file"] == str(inp.resolve())
    assert len(gs["entry_names"]) == 2


def test_setup_skip_when_already_done(tmp_path: Path) -> None:
    """Setup is skipped when phases.setup is already done."""
    inp = _write_input(tmp_path)
    out = tmp_path / "out"
    runner = CliRunner()
    # First run: complete setup
    result1 = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result1.exit_code == 0

    # Second run: setup should be skipped (no version prompt needed)
    result2 = runner.invoke(cli, [str(inp), "--output-dir", str(out)])
    assert result2.exit_code == 0

    gs = json.loads((out / ".state" / "global.json").read_text())
    assert gs["phases"]["setup"] == "done"


def test_invalid_input_rejected(tmp_path: Path) -> None:
    """Invalid JSON input exits with code 1 and error message."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"results": [{"init_file": "x.el"}]}')
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(cli, [str(bad_file), "--output-dir", str(out)])
    assert result.exit_code == 1


def test_missing_input_rejected(tmp_path: Path) -> None:
    """Missing input file exits with code 2 (usage error)."""
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(cli, [str(tmp_path / "nope.json"), "--output-dir", str(out)])
    assert result.exit_code == 2


def test_directory_input_rejected(tmp_path: Path) -> None:
    """Passing a directory as STALE_INITS_FILE exits with code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, [str(tmp_path), "--output-dir", str(tmp_path / "out")])
    assert result.exit_code == 2
    assert "is a directory, not a file" in result.output
