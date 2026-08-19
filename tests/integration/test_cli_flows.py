# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from tsdbenv.cli import main

@pytest.fixture
def cli_runner():
    return CliRunner()

def test_cli_version(cli_runner):
    """Test --version flag."""
    result = cli_runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "tsdbenv" in result.output

def test_cli_list_empty(cli_runner):
    """Test list with no containers."""
    with patch("tsdbenv.cli.cli_state.state_tracker.load_containers") as mock_load:
        mock_load.return_value = []
        result = cli_runner.invoke(main, ["list"])
        assert "No containers found" in result.output

def test_cli_new_with_flags(cli_runner):
    """Test creating container with flags."""
    result = cli_runner.invoke(main, [
        "new",
        "--postgres", "14",
        "--timescaledb", "2.8.0",
        "--name", "testdb",
        "--bind-ip", "127.0.0.1",
    ], input="n\n")
    assert result.exit_code == 0 or "created successfully" in result.output

def test_cli_remove_not_found(cli_runner):
    """Test removing nonexistent container."""
    with patch("tsdbenv.cli.cli_state.state_tracker.delete_container") as mock_delete:
        mock_delete.side_effect = KeyError("Container not found")
        result = cli_runner.invoke(main, ["remove", "nonexistent"])
        assert "not found" in result.output.lower() or result.exit_code != 0
