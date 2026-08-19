# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

"""Real Docker integration tests using actual Docker containers.

These tests verify the complete Docker lifecycle with real containers.
They require Docker to be running and will create/destroy test containers.

Skip gracefully if Docker is unavailable.
"""

import uuid
from typing import Generator

import docker
import docker.errors
import pytest

from tsdbenv.docker_utils import DockerClient


def _is_docker_available() -> bool:
    """Check if Docker is available for integration tests."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def cleanup_containers():
    """Generator that tracks containers to clean up after tests."""
    containers_to_cleanup = []

    def _register_container(container_id: str) -> None:
        containers_to_cleanup.append(container_id)

    yield _register_container

    # Cleanup: remove all registered containers
    if containers_to_cleanup:
        try:
            client = docker.from_env()
            for cid in containers_to_cleanup:
                try:
                    container = client.containers.get(cid)
                    if container.status in ["running", "paused"]:
                        container.stop(timeout=5)
                    container.remove(force=True)
                except docker.errors.NotFound:
                    pass  # Already removed
                except Exception:
                    pass  # Ignore cleanup errors
        except Exception:
            pass  # Docker not available


@pytest.mark.skipif(
    not _is_docker_available(),
    reason="Docker not available",
)
class TestDockerRealLifecycle:
    """Real Docker integration tests."""

    def test_full_container_lifecycle(self, cleanup_containers):
        """Test full container lifecycle: create → list → logs → stop → remove.

        This is an end-to-end test with a real container.
        """

        client = DockerClient()
        container_name = f"tsdbenv-test-{uuid.uuid4().hex[:8]}"

        try:
            # Create container directly (skip wait_for_postgres)
            # Use sleep to keep container running
            raw_container = client.client.containers.run(
                "alpine:latest",
                "sleep 3600",
                name=container_name,
                environment={"TEST": "value"},
                detach=True,
                remove=False,
            )
            container_id = raw_container.id
            cleanup_containers(container_id)
            assert container_id is not None
            assert len(container_id) > 0

            # List containers (should include our new one)
            containers = client.list_containers()
            container_names = [c["name"] for c in containers]
            assert container_name in container_names

            # Find our container in the list
            our_container = next(c for c in containers if c["name"] == container_name)
            assert our_container["status"] == "running"
            assert our_container["id"] == container_id

            # Get logs
            logs = client.get_container_logs(container_id)
            assert isinstance(logs, str)

            # Stop container
            client.stop_container(container_id)
            containers = client.list_containers()
            stopped_container = next(c for c in containers if c["id"] == container_id)
            assert stopped_container["status"] == "exited"

            # Restart container
            client.start_container(container_id)
            containers = client.list_containers()
            restarted_container = next(c for c in containers if c["id"] == container_id)
            assert restarted_container["status"] == "running"

            # Remove container
            client.remove_container(container_id)
            containers = client.list_containers()
            container_ids = [c["id"] for c in containers]
            assert container_id not in container_ids

        except docker.errors.NotFound as e:
            pytest.fail(f"Docker container not found: {e}")

    def test_multiple_containers(self, cleanup_containers):
        """Test creating, listing, and removing multiple containers.

        This verifies the system handles multiple containers correctly.
        """

        client = DockerClient()
        container_ids = []

        try:
            # Create 3 containers directly (skip wait_for_postgres)
            for i in range(3):
                container_name = f"tsdbenv-multi-{uuid.uuid4().hex[:8]}"
                raw_container = client.client.containers.run(
                    "alpine:latest",
                    "sleep 3600",
                    name=container_name,
                    detach=True,
                    remove=False,
                )
                container_id = raw_container.id
                container_ids.append(container_id)
                cleanup_containers(container_id)

            # List and verify all 3 are present
            containers = client.list_containers()
            listed_ids = [c["id"] for c in containers]
            for cid in container_ids:
                assert cid in listed_ids

            # Stop one container
            client.stop_container(container_ids[0])
            containers = client.list_containers()
            stopped = next(c for c in containers if c["id"] == container_ids[0])
            assert stopped["status"] == "exited"

            # Remove one container
            client.remove_container(container_ids[0])
            containers = client.list_containers()
            listed_ids = [c["id"] for c in containers]
            assert container_ids[0] not in listed_ids

            # Verify the other 2 still exist
            for cid in container_ids[1:]:
                assert cid in listed_ids

            # Remove remaining containers
            for cid in container_ids[1:]:
                client.remove_container(cid)

            # Verify all are gone
            containers = client.list_containers()
            listed_ids = [c["id"] for c in containers]
            for cid in container_ids:
                assert cid not in listed_ids

        except docker.errors.NotFound as e:
            pytest.fail(f"Docker container not found during multi-container test: {e}")

    def test_start_stop_not_found(self):
        """Test error handling when container doesn't exist."""

        client = DockerClient()
        fake_id = "nonexistent_container_xyz123"

        with pytest.raises(docker.errors.NotFound):
            client.start_container(fake_id)

        with pytest.raises(docker.errors.NotFound):
            client.stop_container(fake_id)

        with pytest.raises(docker.errors.NotFound):
            client.remove_container(fake_id)

    def test_get_logs_not_found(self):
        """Test error handling when getting logs from non-existent container."""

        client = DockerClient()
        fake_id = "nonexistent_container_xyz123"

        with pytest.raises(docker.errors.NotFound):
            client.get_container_logs(fake_id)
