# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for integration tests."""
    with patch("docker.from_env") as mock:
        yield mock


@pytest.fixture
def mock_docker_container():
    """Mock Docker container object."""
    mock_container = MagicMock()
    mock_container.id = "abc123def456"
    mock_container.status = "running"
    mock_container.logs.return_value = b"PostgreSQL started\n"
    return mock_container
