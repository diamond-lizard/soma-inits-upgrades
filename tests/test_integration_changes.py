"""Integration tests for entry change detection during Setup."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from soma_inits_upgrades.main import cli

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
    runner = CliRunner()
    result = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result.exit_code == 0
    gs_path = out / ".state" / "global.json"
    gs = json.loads(gs_path.read_text())
    gs["phases"]["setup"] = "pending"
    gs_path.write_text(json.dumps(gs))
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
    _write_input(tmp_path, new_entries)
    runner = CliRunner()
    result = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result.exit_code == 0
    es = json.loads((out / ".state" / "a.el.json").read_text())
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
    _write_input(tmp_path, new_entries)
    runner = CliRunner()
    result = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result.exit_code == 0
    es = json.loads((out / ".state" / "a.el.json").read_text())
    assert es["pinned_ref"] == "new222"
