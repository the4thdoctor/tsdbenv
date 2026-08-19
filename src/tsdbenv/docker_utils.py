# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from typing import Optional, List, Dict
import shutil

class DockerClient:
    """Wrapper around Docker SDK (stubs for Phase 2)."""

    def __init__(self):
        """Initialize Docker client."""
        self._verify_docker()

    def check_docker_installed(self) -> bool:
        """Check if Docker is installed and running."""
        return shutil.which("docker") is not None

    def _verify_docker(self) -> None:
        """Verify Docker is installed. Raise if not."""
        if not self.check_docker_installed():
            raise RuntimeError(
                "Docker is not installed or not in PATH. "
                "Please install Docker: https://docs.docker.com/get-docker/"
            )

    def create_container(
        self,
        image: str,
        name: str,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict]] = None,
    ) -> str:
        """Create a Docker container (STUB for Phase 2)."""
        return f"mock_{name}_id_12345"

    def start_container(self, container_id: str) -> None:
        """Start a container (STUB for Phase 2)."""
        pass

    def stop_container(self, container_id: str) -> None:
        """Stop a container (STUB for Phase 2)."""
        pass

    def remove_container(self, container_id: str) -> None:
        """Remove a container (STUB for Phase 2)."""
        pass

    def get_container_logs(self, container_id: str) -> str:
        """Get container logs (STUB for Phase 2)."""
        return "[Mock logs] Container is running successfully."

    def list_containers(self) -> List[Dict]:
        """List all containers (STUB for Phase 2)."""
        return []
