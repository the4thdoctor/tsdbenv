# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from unittest.mock import MagicMock, patch

import docker.errors
import pytest

from tsdbenv.docker_utils import DockerClient


@pytest.fixture
def mock_client():
    """Patch docker.from_env to return a MagicMock client."""
    with patch("tsdbenv.docker_utils.docker.from_env") as mock_from_env:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_from_env.return_value = fake_client
        yield fake_client


def test_init_success(mock_client):
    """DockerClient initializes when the daemon is reachable."""
    client = DockerClient()
    assert client.client is mock_client
    mock_client.ping.assert_called_once()


def test_init_raises_when_docker_not_running():
    """DockerClient raises RuntimeError when ping fails."""
    with patch("tsdbenv.docker_utils.docker.from_env") as mock_from_env:
        fake_client = MagicMock()
        fake_client.ping.side_effect = Exception("connection refused")
        mock_from_env.return_value = fake_client
        with pytest.raises(RuntimeError, match="Docker daemon is not running"):
            DockerClient()


def test_check_docker_installed_true(mock_client):
    client = DockerClient()
    assert client.check_docker_installed() is True


def test_check_docker_installed_false(mock_client):
    client = DockerClient()
    mock_client.ping.side_effect = Exception("boom")
    assert client.check_docker_installed() is False


def test_create_container_success(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    fake_container.id = "abc123"
    mock_client.containers.run.return_value = fake_container

    with patch.object(client, "wait_for_postgres", return_value=True) as mock_wait:
        container_id = client.create_container(
            image="postgres:14-alpine",
            name="testdb",
            environment={"POSTGRES_PASSWORD": "postgres"},
            ports={5432: 5432},
        )

    assert container_id == "abc123"
    mock_wait.assert_called_once_with("abc123")
    mock_client.containers.run.assert_called_once()
    _, kwargs = mock_client.containers.run.call_args
    assert kwargs["name"] == "testdb"
    assert kwargs["detach"] is True
    assert kwargs["remove"] is False


def test_create_container_port_conflict(mock_client):
    client = DockerClient()
    mock_client.containers.run.side_effect = docker.errors.APIError(
        "Address already in use"
    )

    with pytest.raises(docker.errors.APIError, match="Port already in use"):
        client.create_container(
            image="postgres:14-alpine",
            name="testdb",
            environment={},
            ports={5432: 5432},
        )


def test_create_container_other_api_error_propagates(mock_client):
    client = DockerClient()
    mock_client.containers.run.side_effect = docker.errors.APIError("some other error")

    with pytest.raises(docker.errors.APIError, match="some other error"):
        client.create_container(
            image="postgres:14-alpine",
            name="testdb",
            environment={},
            ports={5432: 5432},
        )


def test_start_container(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    mock_client.containers.get.return_value = fake_container

    client.start_container("abc123")

    mock_client.containers.get.assert_called_once_with("abc123")
    fake_container.start.assert_called_once()


def test_stop_container(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    mock_client.containers.get.return_value = fake_container

    client.stop_container("abc123")

    fake_container.stop.assert_called_once_with(timeout=10)


def test_remove_container_running(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    fake_container.status = "running"
    mock_client.containers.get.return_value = fake_container

    client.remove_container("abc123")

    fake_container.stop.assert_called_once_with(timeout=10)
    fake_container.remove.assert_called_once_with(force=True)


def test_remove_container_already_stopped(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    fake_container.status = "exited"
    mock_client.containers.get.return_value = fake_container

    client.remove_container("abc123")

    fake_container.stop.assert_not_called()
    fake_container.remove.assert_called_once_with(force=True)


def test_get_container_logs(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    fake_container.logs.return_value = (
        b"database system is ready to accept connections\n"
    )
    mock_client.containers.get.return_value = fake_container

    logs = client.get_container_logs("abc123")

    assert "database system is ready to accept connections" in logs
    fake_container.logs.assert_called_once_with(stdout=True, stderr=True)


def test_list_containers(mock_client):
    client = DockerClient()
    fake_container = MagicMock()
    fake_container.id = "abc123"
    fake_container.name = "testdb"
    fake_container.status = "running"
    fake_container.ports = {"5432/tcp": [{"HostPort": "5432"}]}
    mock_client.containers.list.return_value = [fake_container]

    result = client.list_containers()

    assert result == [
        {
            "id": "abc123",
            "name": "testdb",
            "status": "running",
            "ports": {"5432/tcp": [{"HostPort": "5432"}]},
        }
    ]
    mock_client.containers.list.assert_called_once_with(all=True)


def test_wait_for_postgres_ready_immediately(mock_client):
    client = DockerClient()
    with patch.object(
        client,
        "get_container_logs",
        return_value="database system is ready to accept connections",
    ):
        assert client.wait_for_postgres("abc123", timeout=5) is True


def test_wait_for_postgres_timeout(mock_client):
    client = DockerClient()
    with patch.object(client, "get_container_logs", return_value="starting up..."):
        with patch("tsdbenv.docker_utils.time.sleep"):
            with pytest.raises(TimeoutError, match="PostgreSQL not ready after"):
                client.wait_for_postgres("abc123", timeout=1)
