# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import json
from datetime import datetime

import pytest

from tsdbenv.models import Container, PostgresConfig, VersionMatrix


def test_container_creation():
    """Test Container initialization."""
    c = Container(
        name="mydb",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime(2026, 8, 19, 10, 0),
        last_accessed_at=datetime(2026, 8, 19, 14, 0),
        config_path=None,
        docker_id="abc123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd",
    )
    assert c.name == "mydb"
    assert c.postgres_version == "14"


def test_container_to_json(sample_container):
    """Test Container serialization to JSON."""
    json_str = sample_container.model_dump_json()
    data = json.loads(json_str)
    assert data["name"] == "testdb"
    assert data["postgres_version"] == "14"


def test_container_from_json(sample_container):
    """Test Container deserialization from JSON."""
    json_str = sample_container.model_dump_json()
    restored = Container.model_validate_json(json_str)
    assert restored.name == sample_container.name
    assert restored.port == sample_container.port


def test_version_matrix_is_compatible(sample_version_matrix):
    """Test VersionMatrix.is_compatible()."""
    assert sample_version_matrix.is_compatible("14", "2.8.0") is True
    assert sample_version_matrix.is_compatible("14", "2.11.0") is False
    assert sample_version_matrix.is_compatible("16", "2.8.0") is False


def test_postgres_config_to_env_dict(sample_postgres_config):
    """Test PostgresConfig.to_env_dict()."""
    env_dict = sample_postgres_config.to_env_dict()
    assert env_dict["shared_buffers"] == "256MB"
    assert env_dict["work_mem"] == "4MB"


def test_postgres_config_json_roundtrip(sample_postgres_config):
    """Test PostgresConfig serialization/deserialization."""
    json_str = sample_postgres_config.model_dump_json()
    restored = PostgresConfig.model_validate_json(json_str)
    assert restored.raw_settings == sample_postgres_config.raw_settings
