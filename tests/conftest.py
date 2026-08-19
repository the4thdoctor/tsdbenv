# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
import tempfile
from pathlib import Path

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
