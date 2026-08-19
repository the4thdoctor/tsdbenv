# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tsdbenv.state_tracker import StateTracker
from tsdbenv.models import Container

def test_state_tracker_init(temp_state_dir):
    """Test StateTracker initialization."""
    st = StateTracker(state_dir=temp_state_dir)
    assert st.state_dir == temp_state_dir
    assert st.state_file == temp_state_dir / "containers.json"

def test_save_and_load_container(temp_state_dir, sample_container):
    """Test saving and loading a container."""
    st = StateTracker(state_dir=temp_state_dir)
    st.save_container(sample_container)

    containers = st.load_containers()
    assert len(containers) == 1
    assert containers[0].name == "testdb"

def test_save_multiple_containers(temp_state_dir, sample_container):
    """Test saving multiple containers."""
    st = StateTracker(state_dir=temp_state_dir)
    st.save_container(sample_container)

    container2 = Container(
        name="mydb2",
        postgres_version="15",
        timescaledb_version="2.9.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="xyz789",
        port=5433,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd2",
    )
    st.save_container(container2)

    containers = st.load_containers()
    assert len(containers) == 2

def test_delete_container(temp_state_dir, sample_container):
    """Test deleting a container from state."""
    st = StateTracker(state_dir=temp_state_dir)
    st.save_container(sample_container)

    st.delete_container("testdb")

    containers = st.load_containers()
    assert len(containers) == 0

def test_mark_accessed(temp_state_dir, sample_container):
    """Test updating last_accessed_at timestamp."""
    st = StateTracker(state_dir=temp_state_dir)
    st.save_container(sample_container)

    before = sample_container.last_accessed_at
    st.mark_accessed("testdb")

    containers = st.load_containers()
    after = containers[0].last_accessed_at
    assert after > before

def test_get_stale_containers(temp_state_dir):
    """Test detecting stale containers (not accessed for 5+ days)."""
    st = StateTracker(state_dir=temp_state_dir)

    fresh = Container(
        name="fresh",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="fresh123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd",
    )
    st.save_container(fresh)

    stale = Container(
        name="stale",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now() - timedelta(days=10),
        last_accessed_at=datetime.now() - timedelta(days=6),
        config_path=None,
        docker_id="stale123",
        port=5433,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd",
    )
    st.save_container(stale)

    stale_list = st.get_stale_containers(days=5)
    assert len(stale_list) == 1
    assert stale_list[0].name == "stale"

def test_load_containers_empty(temp_state_dir):
    """Test loading containers when state file doesn't exist."""
    st = StateTracker(state_dir=temp_state_dir)
    containers = st.load_containers()
    assert containers == []
