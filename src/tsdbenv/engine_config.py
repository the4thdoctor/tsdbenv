# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-20

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Engine(str, Enum):
    """Container engine selection: Docker or Podman."""

    DOCKER = "docker"
    PODMAN = "podman"


def get_socket_path(engine: Engine) -> str:
    """
    Get socket path for the specified container engine.

    Args:
        engine: Engine.DOCKER or Engine.PODMAN

    Returns:
        Socket path: /var/run/docker.sock for Docker,
        /run/podman/podman.sock for Podman
    """
    socket_paths = {
        Engine.DOCKER: "/var/run/docker.sock",
        Engine.PODMAN: "/run/podman/podman.sock",
    }
    return socket_paths[engine]


def get_engine_from_cli_or_env(cli_engine: Optional[str] = None) -> Engine:
    """
    Determine container engine from CLI arg or environment variable.

    Precedence: explicit CLI arg > TSDBENV_ENGINE env var > default (Docker).

    Args:
        cli_engine: Optional engine name from CLI (--engine flag).
                   Accepts "docker" or "podman" (case-insensitive).

    Returns:
        Engine.DOCKER or Engine.PODMAN

    Raises:
        ValueError: If cli_engine is provided but is invalid.
    """
    # 1. Check explicit CLI argument
    if cli_engine is not None:
        cli_engine_lower = cli_engine.lower().strip()
        try:
            return Engine(cli_engine_lower)
        except ValueError:
            raise ValueError(
                f"Invalid engine '{cli_engine}'. Must be 'docker' or 'podman'."
            )

    # 2. Check environment variable
    env_engine = os.getenv("TSDBENV_ENGINE")
    if env_engine is not None:
        env_engine_lower = env_engine.lower().strip()
        try:
            return Engine(env_engine_lower)
        except ValueError:
            raise ValueError(
                f"Invalid TSDBENV_ENGINE value '{env_engine}'. "
                f"Must be 'docker' or 'podman'."
            )

    # 3. Default to Docker
    return Engine.DOCKER


@dataclass
class EngineConfig:
    """Configuration for container engine (Docker or Podman)."""

    engine: Engine
    socket_path: str
    network_mode: str

    def __post_init__(self):
        """Validate and set socket_path based on engine if not provided."""
        if not self.socket_path:
            self.socket_path = get_socket_path(self.engine)

        # Validate network_mode is set
        if not self.network_mode:
            raise ValueError("network_mode must be specified")

    @staticmethod
    def from_engine(engine: Engine) -> "EngineConfig":
        """
        Create EngineConfig from an Engine enum.

        Sets network mode based on engine:
        - Docker: 'bridge'
        - Podman: 'slirp4netns'

        Args:
            engine: Engine.DOCKER or Engine.PODMAN

        Returns:
            EngineConfig instance with appropriate defaults
        """
        socket_path = get_socket_path(engine)

        # Set network mode based on engine
        network_modes = {
            Engine.DOCKER: "bridge",
            Engine.PODMAN: "slirp4netns",
        }
        network_mode = network_modes[engine]

        return EngineConfig(
            engine=engine,
            socket_path=socket_path,
            network_mode=network_mode,
        )

    @staticmethod
    def from_cli_or_env(cli_engine: Optional[str] = None) -> "EngineConfig":
        """
        Create EngineConfig from CLI arg or environment variable.

        Uses precedence: CLI > TSDBENV_ENGINE env var > Docker (default).

        Args:
            cli_engine: Optional engine name from CLI.

        Returns:
            EngineConfig instance with appropriate engine and defaults

        Raises:
            ValueError: If engine selection is invalid
        """
        engine = get_engine_from_cli_or_env(cli_engine)
        return EngineConfig.from_engine(engine)
