"""Integration tests: Setup stage input validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from soma_inits_upgrades.main import cli

if TYPE_CHECKING:
    from pathlib import Path


def test_invalid_input_rejected(tmp_path: Path) -> None:
    """Invalid JSON input exits with code 1 and error message."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"results": [{"init_file": "x.el"}]}')
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        cli, [str(bad_file), "--output-dir", str(out)],
    )
    assert result.exit_code == 1


def test_missing_input_rejected(tmp_path: Path) -> None:
    """Missing input file exits with code 2 (usage error)."""
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [str(tmp_path / "nope.json"), "--output-dir", str(out)],
    )
    assert result.exit_code == 2


def test_directory_input_rejected(tmp_path: Path) -> None:
    """Passing a directory as STALE_INITS_FILE exits with code 2."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [str(tmp_path), "--output-dir", str(tmp_path / "out")],
    )
    assert result.exit_code == 2
    assert "is a directory, not a file" in result.output
