"""Tests for CLI argument parsing (main.py)."""

from click.testing import CliRunner

from soma_inits_upgrades.main import cli


def test_cli_accepts_required_argument() -> None:
    """Verify the click command accepts the required positional argument."""
    runner = CliRunner()
    result = runner.invoke(cli, ["some-file.json"])
    assert result.exit_code == 0


def test_cli_rejects_missing_argument() -> None:
    """Verify missing argument exits with code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 2


def test_cli_accepts_output_dir_option() -> None:
    """Verify --output-dir option is accepted."""
    runner = CliRunner()
    result = runner.invoke(cli, ["some-file.json", "--output-dir", "/tmp/out"])
    assert result.exit_code == 0
    assert "/tmp/out" in result.output
