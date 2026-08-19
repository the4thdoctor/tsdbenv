# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import re
from pathlib import Path

from tsdbenv.models import PostgresConfig


class ConfigHandler:
    """Parses PostgreSQL configuration files."""

    @staticmethod
    def parse_simple_kv(path: Path) -> PostgresConfig:
        """Parse simple key=value configuration file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        settings = {}
        for line in path.read_text().strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()

        return PostgresConfig(
            raw_settings=settings,
            source_file=str(path),
            is_valid=True,
        )

    @staticmethod
    def parse_postgresql_conf(path: Path) -> PostgresConfig:
        """Parse full postgresql.conf configuration file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        settings = {}
        for line in path.read_text().strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Match "key = value" or key=value
            match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                settings[key] = value.strip()

        return PostgresConfig(
            raw_settings=settings,
            source_file=str(path),
            is_valid=True,
        )

    @staticmethod
    def parse_file(path: Path) -> PostgresConfig:
        """Auto-detect format and parse config file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        content = path.read_text()
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        if lines:
            kv_count = sum(1 for line in lines if "=" in line)
            if kv_count / len(lines) > 0.8:
                return ConfigHandler.parse_simple_kv(path)

        return ConfigHandler.parse_postgresql_conf(path)
