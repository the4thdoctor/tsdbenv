# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from tsdbenv.models import Container, VersionMatrix, PostgresConfig

@pytest.fixture
def temp_state_dir():
    """Create temporary directory for test state files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_home_dir(temp_state_dir, monkeypatch):
    """Mock home directory for tsdbenv state."""
    monkeypatch.setenv("HOME", str(temp_state_dir))
    return temp_state_dir

@pytest.fixture
def sample_container():
    """Provide a sample Container for testing."""
    return Container(
        name="testdb",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime(2026, 8, 19, 10, 0),
        last_accessed_at=datetime(2026, 8, 19, 14, 0),
        config_path=None,
        docker_id="abc123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="secure_pwd",
    )

@pytest.fixture
def sample_version_matrix():
    """Provide a sample VersionMatrix for testing."""
    return VersionMatrix(
        postgres_versions={
            "14": ["2.8.0", "2.9.0", "2.10.0"],
            "15": ["2.10.0", "2.11.0"],
        },
        last_fetched=datetime(2026, 8, 19, 10, 0),
    )

@pytest.fixture
def sample_postgres_config():
    """Provide a sample PostgresConfig for testing."""
    return PostgresConfig(
        raw_settings={
            "shared_buffers": "256MB",
            "work_mem": "4MB",
            "maintenance_work_mem": "64MB",
        },
        source_file="/etc/postgresql/14/main/postgresql.conf",
        is_valid=True,
    )
