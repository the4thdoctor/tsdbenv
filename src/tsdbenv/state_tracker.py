# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from tsdbenv.models import Container


class StateTracker:
    """Manages container state (load/save/stale detection)."""

    STATE_FILE = "containers.json"

    def __init__(self, state_dir: Optional[Path] = None):
        if state_dir is None:
            state_dir = Path.home() / ".tsdbenv"
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / self.STATE_FILE

    def load_containers(self) -> List[Container]:
        """Load all containers from state file."""
        if not self.state_file.exists():
            return []

        try:
            data = json.loads(self.state_file.read_text())
            return [Container(**c) for c in data.get("containers", [])]
        except (json.JSONDecodeError, ValueError):
            return []

    def save_container(self, container: Container) -> None:
        """Save a container to state file (add or update)."""
        containers = self.load_containers()
        containers = [c for c in containers if c.name != container.name]
        containers.append(container)
        self._write_state(containers)

    def delete_container(self, name: str) -> None:
        """Delete a container from state."""
        containers = self.load_containers()
        containers = [c for c in containers if c.name != name]
        self._write_state(containers)

    def mark_accessed(self, name: str) -> None:
        """Update last_accessed_at for a container."""
        containers = self.load_containers()
        for c in containers:
            if c.name == name:
                c.last_accessed_at = datetime.now()
                break
        self._write_state(containers)

    def get_stale_containers(self, days: int = 5) -> List[Container]:
        """Get containers not accessed for N days."""
        containers = self.load_containers()
        now = datetime.now()
        stale = []

        for c in containers:
            age = now - c.last_accessed_at
            if age > timedelta(days=days):
                stale.append(c)

        return stale

    def _write_state(self, containers: List[Container]) -> None:
        """Write containers to state file."""
        data = {"containers": [c.model_dump() for c in containers]}
        data_json = json.dumps(
            data,
            default=lambda x: x.isoformat() if isinstance(x, datetime) else x,
            indent=2,
        )
        self.state_file.write_text(data_json)
