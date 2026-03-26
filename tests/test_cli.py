"""Tests for CLI argument parsing (main.py)."""

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
        {"init_file": "a.el", "repo_url": "https://forge.test/r", "pinned_ref": "abc123"},
    ]}
    p = tmp / "stale.json"
    p.write_text(json.dumps(data))
    return p


def test_cli_rejects_missing_argument() -> None:
    """Verify missing argument exits with code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 2


def test_cli_accepts_required_argument(tmp_path: Path) -> None:
    """Verify the click command accepts the required positional argument."""
    runner = CliRunner()
    inp = _write_input(tmp_path)
    out = tmp_path / "out"
    result = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result.exit_code != 2, "Click rejected the argument"
    assert "Emacs version" in result.output


def test_cli_accepts_output_dir_option(tmp_path: Path) -> None:
    """Verify --output-dir option is accepted."""
    runner = CliRunner()
    inp = _write_input(tmp_path)
    out = tmp_path / "out"
    result = runner.invoke(cli, [str(inp), "--output-dir", str(out)], input="29.1\n")
    assert result.exit_code != 2, "Click rejected --output-dir"
    assert "Emacs version" in result.output
