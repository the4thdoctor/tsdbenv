# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from tsdbenv.models import VersionMatrix

class VersionManager:
    """Manages PostgreSQL × TimescaleDB compatibility matrix."""

    CACHE_FILE = "version_matrix.json"
    FALLBACK_MATRIX = {
        "14": ["2.8.0", "2.9.0", "2.10.0"],
        "15": ["2.9.0", "2.10.0", "2.11.0"],
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize VersionManager.

        Args:
            cache_dir: Directory for caching matrix (default: ~/.tsdbenv)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".tsdbenv"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.matrix: Optional[VersionMatrix] = None

    def is_compatible(self, postgres_ver: str, timescaledb_ver: str) -> bool:
        """Check if versions are compatible."""
        if self.matrix is None:
            self.matrix = self.get_or_fetch()
        return self.matrix.is_compatible(postgres_ver, timescaledb_ver)

    def load_from_cache(self) -> Optional[VersionMatrix]:
        """Load compatibility matrix from cache file."""
        cache_file = self.cache_dir / self.CACHE_FILE
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            return VersionMatrix(
                postgres_versions=data["matrix"],
                last_fetched=datetime.fromisoformat(data["fetched_at"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def fetch_from_tigerdata(self) -> VersionMatrix:
        """Fetch matrix from TigerData docs (stub for now)."""
        # Phase 3: implement actual fetching from TigerData URL
        return VersionMatrix(
            postgres_versions=self.FALLBACK_MATRIX,
            last_fetched=datetime.now(),
        )

    def get_or_fetch(self) -> VersionMatrix:
        """Get matrix from cache, or fetch if unavailable."""
        cached = self.load_from_cache()
        if cached is not None:
            return cached
        return self.fetch_from_tigerdata()
