# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from datetime import datetime
from tsdbenv.models import Container, VersionMatrix, PostgresConfig

@pytest.fixture
def sample_container():
    """Sample Container for testing."""
    return Container(
        name="testdb",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime(2026, 8, 19, 10, 30),
        last_accessed_at=datetime(2026, 8, 19, 14, 15),
        config_path=None,
        docker_id="abc123def456",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="test_password_123",
    )

@pytest.fixture
def sample_version_matrix():
    """Sample VersionMatrix for testing."""
    return VersionMatrix(
        postgres_versions={
            "14": ["2.8.0", "2.9.0", "2.10.0"],
            "15": ["2.9.0", "2.10.0", "2.11.0"],
        },
        last_fetched=datetime(2026, 8, 19, 10, 0),
    )

@pytest.fixture
def sample_postgres_config():
    """Sample PostgresConfig for testing."""
    return PostgresConfig(
        raw_settings={"shared_buffers": "256MB", "work_mem": "4MB"},
        source_file=None,
        is_valid=True,
    )
