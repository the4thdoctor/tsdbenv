# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-20

from unittest.mock import MagicMock, patch

import pytest

from tsdbenv.docker_utils import DockerClient


def test_docker_client_default_engine():
    """Test DockerClient() defaults to Docker engine."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        DockerClient()

        # Should be called with Docker socket path
        mock_docker_client.assert_called_once_with(
            base_url="unix:///var/run/docker.sock"
        )


def test_docker_client_explicit_docker_engine():
    """Test DockerClient(engine='docker') uses Docker socket."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        DockerClient(engine="docker")

        # Should be called with Docker socket path
        mock_docker_client.assert_called_once_with(
            base_url="unix:///var/run/docker.sock"
        )


def test_docker_client_explicit_podman_engine():
    """Test DockerClient(engine='podman') uses Podman socket."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        DockerClient(engine="podman")

        # Should be called with Podman socket path
        mock_docker_client.assert_called_once_with(
            base_url="unix:///run/podman/podman.sock"
        )


def test_docker_client_case_insensitive_engine():
    """Test DockerClient engine parameter is case-insensitive."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        DockerClient(engine="PODMAN")

        # Should be called with Podman socket path (case-insensitive)
        mock_docker_client.assert_called_once_with(
            base_url="unix:///run/podman/podman.sock"
        )


def test_docker_client_docker_socket_not_running():
    """Test error message when Docker socket is not available."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        # Simulate socket connection failure
        mock_docker_client.side_effect = Exception("Cannot connect to Unix socket")

        with pytest.raises(
            RuntimeError,
            match="Docker is not running or not installed.*brew install docker",
        ):
            DockerClient(engine="docker")


def test_docker_client_podman_socket_not_running():
    """Test error message when Podman socket is not available."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        # Simulate socket connection failure
        mock_docker_client.side_effect = Exception("Cannot connect to Unix socket")

        with pytest.raises(
            RuntimeError,
            match="Podman is not running or not installed.*brew install podman",
        ):
            DockerClient(engine="podman")


def test_docker_client_invalid_engine():
    """Test error when invalid engine is specified."""
    with pytest.raises(ValueError, match="Invalid engine"):
        DockerClient(engine="invalid")


def test_docker_client_engine_from_env_variable():
    """Test DockerClient respects TSDBENV_ENGINE environment variable."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        with patch.dict("os.environ", {"TSDBENV_ENGINE": "podman"}):
            DockerClient()

            # Should use Podman socket when env var is set
            mock_docker_client.assert_called_once_with(
                base_url="unix:///run/podman/podman.sock"
            )


def test_docker_client_cli_overrides_env():
    """Test CLI engine parameter overrides TSDBENV_ENGINE environment variable."""
    with patch("tsdbenv.docker_utils.docker.DockerClient") as mock_docker_client:
        fake_client = MagicMock()
        fake_client.ping.return_value = True
        mock_docker_client.return_value = fake_client

        with patch.dict("os.environ", {"TSDBENV_ENGINE": "podman"}):
            # Explicit docker engine should override env var
            DockerClient(engine="docker")

            # Should use Docker socket even though env var says podman
            mock_docker_client.assert_called_once_with(
                base_url="unix:///var/run/docker.sock"
            )
