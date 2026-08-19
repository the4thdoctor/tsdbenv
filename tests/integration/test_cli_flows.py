# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from unittest.mock import patch

import pytest
from click.testing import CliRunner

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
    with patch(
        "tsdbenv.cli.cli_state.docker_client.create_container"
    ) as mock_docker, patch("tsdbenv.cli.cli_state.state_tracker.save_container"):
        mock_docker.return_value = "container-123"

        result = cli_runner.invoke(
            main,
            [
                "new",
                "--postgres",
                "14",
                "--timescaledb",
                "2.8.0",
                "--name",
                "testdb",
                "--port",
                "5432",
                "--bind-ip",
                "127.0.0.1",
            ],
            input="n\n",
        )
    assert result.exit_code == 0 or "created successfully" in result.output
    assert mock_docker.called


def test_cli_remove_not_found(cli_runner):
    """Test removing nonexistent container."""
    with patch("tsdbenv.cli.cli_state.state_tracker.delete_container") as mock_delete:
        mock_delete.side_effect = KeyError("Container not found")
        result = cli_runner.invoke(main, ["remove", "nonexistent"])
        assert "not found" in result.output.lower() or result.exit_code != 0


def test_cli_new_interactive_prompts(cli_runner):
    """Test interactive container creation with all prompts."""
    with patch(
        "tsdbenv.cli.cli_state.version_manager.is_compatible"
    ) as mock_compat, patch(
        "tsdbenv.cli.cli_state.docker_client.create_container"
    ) as mock_docker, patch(
        "tsdbenv.cli.cli_state.state_tracker.save_container"
    ) as mock_save, patch(
        "tsdbenv.cli.NetworkValidator.validate_bind_ip"
    ) as mock_validate:
        mock_compat.return_value = True
        mock_docker.return_value = "container-123"
        mock_validate.return_value = (True, None)

        result = cli_runner.invoke(
            main,
            ["new"],
            input="14\n2.8.0\ntestdb\n5432\nn\nlocalhost\n",
        )
        assert result.exit_code == 0
        assert mock_docker.called


def test_cli_logs_with_selection(cli_runner):
    """Test logs command with container selection."""
    from datetime import datetime

    from tsdbenv.models import Container

    container = Container(
        name="test",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="test-123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="password",
    )

    with patch(
        "tsdbenv.cli.cli_state.state_tracker.load_containers"
    ) as mock_load, patch(
        "tsdbenv.cli.cli_state.docker_client.get_container_logs"
    ) as mock_logs, patch(
        "tsdbenv.cli.cli_state.state_tracker.mark_accessed"
    ) as mock_accessed:
        mock_load.return_value = [container]
        mock_logs.return_value = "Container logs here"

        result = cli_runner.invoke(main, ["logs"], input="test\n")
        assert result.exit_code == 0
        assert "Container logs here" in result.output
        assert mock_accessed.called


def test_cli_remove_with_confirmation(cli_runner):
    """Test remove command with user confirmation."""
    from datetime import datetime

    from tsdbenv.models import Container

    container = Container(
        name="test",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="test-123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="password",
    )

    with patch(
        "tsdbenv.cli.cli_state.state_tracker.load_containers"
    ) as mock_load, patch(
        "tsdbenv.cli.cli_state.docker_client.remove_container"
    ) as mock_remove, patch(
        "tsdbenv.cli.cli_state.state_tracker.delete_container"
    ) as mock_delete:
        mock_load.return_value = [container]

        result = cli_runner.invoke(main, ["remove", "test"], input="y\n")
        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert mock_remove.called
        assert mock_delete.called


def test_cli_interactive_menu(cli_runner):
    """Test interactive menu selection."""
    with patch("tsdbenv.cli.cli_state.state_tracker.load_containers") as mock_load:
        mock_load.return_value = []
        result = cli_runner.invoke(main, input="list\n")
        assert result.exit_code == 0
        assert "No containers found" in result.output


def test_cli_docker_not_running(cli_runner):
    """Test handling when Docker is not installed."""
    with patch("tsdbenv.cli.cli_state.docker_client", None):
        result = cli_runner.invoke(main)
        assert result.exit_code != 0
        assert "Docker is not installed" in result.output


def test_cli_list_with_containers(cli_runner):
    """Test list command with containers."""
    from datetime import datetime

    from tsdbenv.models import Container

    container1 = Container(
        name="db1",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="id1",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pw1",
    )
    container2 = Container(
        name="db2",
        postgres_version="15",
        timescaledb_version="2.9.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="id2",
        port=5433,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pw2",
    )

    with patch(
        "tsdbenv.cli.cli_state.state_tracker.load_containers"
    ) as mock_load, patch(
        "tsdbenv.cli.cli_state.state_tracker.get_stale_containers"
    ) as mock_stale:
        mock_load.return_value = [container1, container2]
        mock_stale.return_value = []

        result = cli_runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "db1" in result.output
        assert "db2" in result.output
