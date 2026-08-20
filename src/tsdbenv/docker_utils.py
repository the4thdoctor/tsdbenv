# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import docker
import docker.errors

VALID_ENGINES = ("docker", "podman")


class DockerClient:
    """Wrapper around the Docker SDK for container lifecycle management.

    Also supports Podman, since Podman exposes a Docker-compatible REST API
    over a unix socket that the Docker SDK can talk to directly. The engine
    is selected explicitly (via `engine` or the TSDBENV_ENGINE environment
    variable) rather than auto-detected, so behavior stays predictable
    across machines.
    """

    def __init__(self, engine: Optional[str] = None) -> None:
        """Initialize a client for the selected container engine.

        Args:
            engine: "docker" or "podman". Falls back to the TSDBENV_ENGINE
                environment variable, then defaults to "docker".

        Raises:
            ValueError: If engine is not "docker" or "podman".
            RuntimeError: If the selected engine's daemon isn't reachable.
        """
        self.engine = self._resolve_engine(engine)
        self.client = self._connect(self.engine)

    @staticmethod
    def _resolve_engine(engine: Optional[str]) -> str:
        """Resolve the requested engine name from arg, env var, or default."""
        resolved = (
            (engine or os.environ.get("TSDBENV_ENGINE") or "docker").strip().lower()
        )
        if resolved not in VALID_ENGINES:
            raise ValueError(
                f"Unknown container engine '{resolved}'; expected one of {VALID_ENGINES}"
            )
        return resolved

    def _connect(self, engine: str):
        """Connect to the selected engine's daemon and verify it's reachable."""
        if engine == "podman":
            base_url = self._find_podman_socket()
            return self._connect_client(
                lambda: docker.DockerClient(base_url=base_url), "Podman"
            )
        return self._connect_client(docker.from_env, "Docker")

    @staticmethod
    def _connect_client(factory, engine_name: str):
        """Build a client via factory() and verify the daemon responds to ping."""
        try:
            client = factory()
            client.ping()
            return client
        except Exception as e:
            raise RuntimeError(
                f"{engine_name} daemon is not running or not accessible"
            ) from e

    @staticmethod
    def _find_podman_socket() -> str:
        """Locate the Podman API socket, checking env vars then common paths.

        Returns:
            A unix:// URL suitable for docker.DockerClient(base_url=...)

        Raises:
            RuntimeError: If no Podman socket can be found.
        """
        host = os.environ.get("CONTAINER_HOST") or os.environ.get("DOCKER_HOST")
        if host:
            return host

        candidates = []
        xdg_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if xdg_runtime_dir:
            candidates.append(Path(xdg_runtime_dir) / "podman" / "podman.sock")
        uid = getattr(os, "getuid", lambda: None)()
        if uid is not None:
            candidates.append(Path(f"/run/user/{uid}/podman/podman.sock"))
        candidates.append(Path("/run/podman/podman.sock"))

        for socket_path in candidates:
            if socket_path.exists():
                return f"unix://{socket_path}"

        raise RuntimeError(
            "Podman socket not found. Start it with "
            "'systemctl --user enable --now podman.socket' (rootless) or "
            "'podman system service --time=0 unix:///run/podman/podman.sock' "
            "(rootful), or set DOCKER_HOST/CONTAINER_HOST to the socket path."
        )

    def check_docker_installed(self) -> bool:
        """Check if the container engine daemon is running and accessible."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def build_image(
        self,
        dockerfile_dir: str,
        tag: str,
        build_args: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build a Docker image from a Dockerfile.

        Args:
            dockerfile_dir: Directory containing Dockerfile
            tag: Image tag (e.g., "myapp:1.0")
            build_args: Build arguments passed to docker build (optional)

        Returns:
            Image ID

        Raises:
            RuntimeError: If build fails
        """
        try:
            image, build_logs = self.client.images.build(
                path=dockerfile_dir,
                tag=tag,
                buildargs=build_args or {},
                rm=True,  # Remove intermediate containers
            )
            return image.id
        except docker.errors.BuildError as e:
            raise RuntimeError(f"Docker build failed: {e}")

    def create_container(
        self,
        image: str,
        name: str,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict] = None,
        tsdbadmin_password: Optional[str] = None,
        bind_ip: Optional[str] = None,
    ) -> str:
        """Create and start a PostgreSQL + TimescaleDB container.

        Args:
            image: Docker image name (e.g., "postgres:14-alpine")
            name: Container name
            environment: Environment variables dict
            ports: Port mapping {internal: external} (e.g., {5432: 5432})
            volumes: Volume mounts (optional)
            tsdbadmin_password: Password for tsdbadmin user (optional)
            bind_ip: IP address to bind container to (default: 127.0.0.1 for security)

        Returns:
            Container ID (short or long hash)

        Raises:
            docker.errors.APIError: If port is already in use or other Docker errors
        """
        try:
            env = environment or {}
            if tsdbadmin_password:
                env["TSDBADMIN_PASSWORD"] = tsdbadmin_password

            # Secure port binding: default to localhost only if not specified
            bind_ip = bind_ip or "127.0.0.1"

            # Convert ports dict to Docker SDK format: {internal: (bind_ip, external)}
            docker_ports = {}
            if ports:
                for internal_port, external_port in ports.items():
                    docker_ports[f"{internal_port}/tcp"] = (bind_ip, external_port)

            container = self.client.containers.run(
                image,
                name=name,
                environment=env,
                ports=docker_ports or {},
                volumes=volumes or {},
                detach=True,
                remove=False,  # Keep container even if stopped
                hostname=name,
            )
            # Wait for PostgreSQL to be ready
            self.wait_for_postgres(container.id)
            return container.id
        except docker.errors.APIError as e:
            if "Address already in use" in str(e):
                raise docker.errors.APIError(
                    "Port already in use; try a different port"
                )
            raise

    def start_container(self, container_id: str) -> None:
        """Start a stopped container."""
        container = self.client.containers.get(container_id)
        container.start()

    def stop_container(self, container_id: str) -> None:
        """Gracefully stop a running container."""
        container = self.client.containers.get(container_id)
        container.stop(timeout=10)

    def remove_container(self, container_id: str) -> None:
        """Remove a container (stop first if running)."""
        try:
            container = self.client.containers.get(container_id)
            if container.status in ["running", "paused"]:
                container.stop(timeout=10)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass

    def get_container_logs(self, container_id: str) -> str:
        """Get container logs (stdout/stderr)."""
        container = self.client.containers.get(container_id)
        return container.logs(stdout=True, stderr=True).decode("utf-8")

    def list_containers(self) -> List[Dict]:
        """List all containers (running + stopped).

        Returns:
            List of dicts: [{'id': ..., 'name': ..., 'status': ..., 'ports': ...}, ...]
        """
        containers = self.client.containers.list(all=True)
        result = []
        for c in containers:
            result.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "ports": c.ports,
                }
            )
        return result

    def wait_for_postgres(self, container_id: str, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to be ready for connections.

        Polls container logs for "database system is ready" message.

        Args:
            container_id: Container ID
            timeout: Max seconds to wait

        Returns:
            True if ready, False if timeout

        Raises:
            TimeoutError: If PostgreSQL doesn't start within timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                logs = self.get_container_logs(container_id)
                if "database system is ready to accept connections" in logs:
                    return True
            except Exception:
                pass
            time.sleep(1)
        raise TimeoutError(f"PostgreSQL not ready after {timeout}s")
