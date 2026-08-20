# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from unittest.mock import MagicMock, patch

import docker.errors
import pytest

from tsdbenv.docker_utils import DockerClient


@pytest.fixture
def mock_client():
    """Patch docker.DockerClient to return a MagicMock client."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client
        yield fake_client


def test_init_success(mock_client):
    """DockerClient initializes when the daemon is reachable."""
    client = DockerClient()
    assert client.client is mock_client
    mock_client.ping.assert_called_once()


def test_init_with_docker_engine(mock_client):
    """DockerClient initializes with explicit docker engine."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient(engine="docker")

        assert client.client is fake_client
        mock_docker_client.assert_called_once_with(
            base_url="unix:///var/run/docker.sock"
        )
        fake_client.ping.assert_called_once()


def test_init_with_podman_engine(mock_client):
    """DockerClient initializes with explicit podman engine."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient(engine="podman")

        assert client.client is fake_client
        mock_docker_client.assert_called_once_with(
            base_url="unix:///run/podman/podman.sock"
        )
        fake_client.ping.assert_called_once()


def test_init_raises_when_docker_not_running():
    """DockerClient raises RuntimeError when ping fails."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.side_effect = Exception("connection refused")
        mock_docker_client.return_value = fake_client
        with pytest.raises(RuntimeError, match="Docker is not running or not accessible"):
            DockerClient()


def test_init_raises_when_podman_not_running():
    """DockerClient raises RuntimeError with podman install message when podman not running."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.side_effect = Exception("connection refused")
        mock_docker_client.return_value = fake_client
        with pytest.raises(RuntimeError, match="Podman is not running or not accessible"):
            DockerClient(engine="podman")


def test_check_docker_installed_true():
    """Test check_docker_installed returns True when ping succeeds."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        assert client.check_docker_installed() is True


def test_check_docker_installed_false():
    """Test check_docker_installed returns False when ping fails."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.side_effect = Exception("boom")
        mock_docker_client.return_value = fake_client

        # First ping succeeds for __init__, second fails for check_docker_installed
        ping_calls = [True, Exception("boom")]
        fake_client.ping.side_effect = [True, Exception("boom")]

        client = DockerClient()
        assert client.check_docker_installed() is False


def test_create_container_success():
    """Test successful container creation."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_container.id = "abc123"
        fake_client.containers.run.return_value = fake_container

        with patch.object(client, "wait_for_postgres", return_value=True) as mock_wait:
            container_id = client.create_container(
                image="postgres:14-alpine",
                name="testdb",
                environment={"POSTGRES_PASSWORD": "postgres"},
                ports={5432: 5432},
            )

        assert container_id == "abc123"
        mock_wait.assert_called_once_with("abc123")
        fake_client.containers.run.assert_called_once()
        _, kwargs = fake_client.containers.run.call_args
        assert kwargs["name"] == "testdb"
        assert kwargs["detach"] is True
        assert kwargs["remove"] is False


def test_create_container_port_conflict():
    """Test port conflict error handling."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_client.containers.run.side_effect = docker.errors.APIError(
            "Address already in use"
        )

        with pytest.raises(docker.errors.APIError, match="Port already in use"):
            client.create_container(
                image="postgres:14-alpine",
                name="testdb",
                environment={},
                ports={5432: 5432},
            )


def test_create_container_other_api_error_propagates():
    """Test other API errors propagate correctly."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_client.containers.run.side_effect = docker.errors.APIError(
            "some other error"
        )

        with pytest.raises(docker.errors.APIError, match="some other error"):
            client.create_container(
                image="postgres:14-alpine",
                name="testdb",
                environment={},
                ports={5432: 5432},
            )


def test_start_container():
    """Test starting a container."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_client.containers.get.return_value = fake_container

        client.start_container("abc123")

        fake_client.containers.get.assert_called_once_with("abc123")
        fake_container.start.assert_called_once()


def test_stop_container():
    """Test stopping a container."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_client.containers.get.return_value = fake_container

        client.stop_container("abc123")

        fake_container.stop.assert_called_once_with(timeout=10)


def test_remove_container_running():
    """Test removing a running container."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_container.status = "running"
        fake_client.containers.get.return_value = fake_container

        client.remove_container("abc123")

        fake_container.stop.assert_called_once_with(timeout=10)
        fake_container.remove.assert_called_once_with(force=True)


def test_remove_container_already_stopped():
    """Test removing a stopped container."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_container.status = "exited"
        fake_client.containers.get.return_value = fake_container

        client.remove_container("abc123")

        fake_container.stop.assert_not_called()
        fake_container.remove.assert_called_once_with(force=True)


def test_remove_container_not_found():
    """Test removing a container that no longer exists in Docker."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_client.containers.get.side_effect = docker.errors.NotFound(
            "Container not found"
        )

        # Should not raise an exception
        client.remove_container("nonexistent")

        fake_client.containers.get.assert_called_once_with("nonexistent")


def test_get_container_logs():
    """Test getting container logs."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_container.logs.return_value = (
            b"database system is ready to accept connections\n"
        )
        fake_client.containers.get.return_value = fake_container

        logs = client.get_container_logs("abc123")

        assert "database system is ready to accept connections" in logs
        fake_container.logs.assert_called_once_with(stdout=True, stderr=True)


def test_list_containers():
    """Test listing containers."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        fake_container = MagicMock()
        fake_container.id = "abc123"
        fake_container.name = "testdb"
        fake_container.status = "running"
        fake_container.ports = {"5432/tcp": [{"HostPort": "5432"}]}
        fake_client.containers.list.return_value = [fake_container]

        result = client.list_containers()

        assert result == [
            {
                "id": "abc123",
                "name": "testdb",
                "status": "running",
                "ports": {"5432/tcp": [{"HostPort": "5432"}]},
            }
        ]
        fake_client.containers.list.assert_called_once_with(all=True)


def test_wait_for_postgres_ready_immediately():
    """Test wait_for_postgres when database is ready immediately."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        with patch.object(
            client,
            "get_container_logs",
            return_value="database system is ready to accept connections",
        ):
            assert client.wait_for_postgres("abc123", timeout=5) is True


def test_wait_for_postgres_timeout():
    """Test wait_for_postgres timeout."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        client = DockerClient()
        with patch.object(client, "get_container_logs", return_value="starting up..."):
            with patch("tsdbenv.docker_utils.time.sleep"):
                with pytest.raises(TimeoutError, match="PostgreSQL not ready after"):
                    client.wait_for_postgres("abc123", timeout=1)
