"""Tests for error handling: KeyboardInterrupt and --help."""

from __future__ import annotations

from click.testing import CliRunner

from soma_inits_upgrades.main import cli


def test_help_output() -> None:
    """--help produces output and exits with code 0."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "stale elpaca pins" in result.output
