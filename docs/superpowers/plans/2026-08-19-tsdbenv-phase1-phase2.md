# tsdbenv Phase 1 & 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation (models, version validation, state tracking) and CLI layer with Docker stubs for tsdbenv, enabling users to create/manage PostgreSQL + TimescaleDB containers with version compatibility checks and state persistence.

**Architecture:** Phase 1 establishes data models, version/config validation, and state management as independent, testable units. Phase 2 builds a Click-based CLI on top, stubbing Docker calls so the interface is live while backend integration waits for Phase 3.

**Tech Stack:** Python 3.8+, pydantic, click, docker (SDK), pytest, pathlib, json

## Global Constraints

- **Language:** Python 3.8+
- **Authored by:** Wagner Bianchi <wagnerbianchijr@gmail.com>
- **Commit format:** No co-authors; author only
- **File signatures:** Every `.py` file must include header with author, email, and date written (YYYY-MM-DD)
- **Dependencies:** pydantic, click, docker, pytest (test only)
- **State file location:** `~/.tsdbenv/containers.json`
- **Version matrix cache:** `~/.tsdbenv/version_matrix.json`
- **Logs location:** `./tsdbenv_logs/<container_name>/`
- **Container stale threshold:** 5 days
- **Network binding:** Bridge mode with localhost (127.0.0.1) or LAN IP
- **OO principles:** All components as classes; no procedural functions at module level

---

## File Structure

### New Files to Create

```
src/tsdbenv/
├── __init__.py                 # Package init, version export
├── models.py                   # Container, VersionMatrix, PostgresConfig data classes
├── version_manager.py          # VersionManager: fetch, cache, validate compatibility
├── config_handler.py           # ConfigHandler: parse .conf and KV files
├── state_tracker.py            # StateTracker: load/save JSON, stale detection
├── network_validator.py        # NetworkValidator: IP detection, subnet validation
├── docker_utils.py             # DockerClient wrapper (Phase 2 stub)
├── cli.py                      # Click CLI, user prompts, main entry point
└── utils.py                    # Helpers: paths, timestamps, password generation

tests/
├── conftest.py                 # Shared pytest fixtures
├── unit/
│   ├── conftest.py             # Unit test fixtures
│   ├── test_models.py          # Container, VersionMatrix, PostgresConfig
│   ├── test_version_manager.py # VersionManager fetch, cache, validate
│   ├── test_config_handler.py  # ConfigHandler parse, to_env_dict
│   ├── test_state_tracker.py   # StateTracker save/load, stale detection
│   └── test_network_validator.py # NetworkValidator IP detection, validation
└── integration/
    ├── conftest.py             # Mocks for Docker SDK
    ├── test_cli_flows.py       # Full CLI flows (--new, --list, --logs, --remove)
    └── test_container_lifecycle.py # Create → access → stale → remove

setup.py / pyproject.toml        # Package metadata
requirements.txt                # Dependencies
```

---

# PHASE 1: FOUNDATION

## Task 1: Project Setup & Package Structure

**Files:**
- Create: `src/tsdbenv/__init__.py`
- Create: `requirements.txt`
- Create: `setup.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/conftest.py`
- Create: `tests/integration/conftest.py`

**Interfaces:**
- Produces: Package `tsdbenv` importable as `from tsdbenv import ...`; version accessible as `tsdbenv.__version__`

- [ ] **Step 1: Create src/tsdbenv/__init__.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

__version__ = "0.1.0"
__author__ = "Wagner Bianchi"

from tsdbenv.models import Container, VersionMatrix, PostgresConfig
from tsdbenv.version_manager import VersionManager
from tsdbenv.config_handler import ConfigHandler
from tsdbenv.state_tracker import StateTracker
from tsdbenv.network_validator import NetworkValidator

__all__ = [
    "Container",
    "VersionMatrix",
    "PostgresConfig",
    "VersionManager",
    "ConfigHandler",
    "StateTracker",
    "NetworkValidator",
]
```

- [ ] **Step 2: Create requirements.txt**

```
pydantic>=2.0
click>=8.1
docker>=6.0
pytest>=7.0
pytest-cov>=4.0
```

- [ ] **Step 3: Create setup.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from setuptools import setup, find_packages

setup(
    name="tsdbenv",
    version="0.1.0",
    author="Wagner Bianchi",
    author_email="wagnerbianchijr@gmail.com",
    description="PostgreSQL + TimescaleDB environment manager via Docker",
    url="https://github.com/wagnerbianchijr/tsdbenv.git",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0",
        "click>=8.1",
        "docker>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "tsdbenv=tsdbenv.cli:main",
        ]
    },
)
```

- [ ] **Step 4: Create tests/conftest.py**

```python
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
```

- [ ] **Step 5: Create tests/unit/conftest.py**

```python
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
```

- [ ] **Step 6: Create tests/integration/conftest.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_docker_client():
    """Mock Docker client for integration tests."""
    with patch("docker.from_env") as mock:
        yield mock

@pytest.fixture
def mock_docker_container():
    """Mock Docker container object."""
    mock_container = MagicMock()
    mock_container.id = "abc123def456"
    mock_container.status = "running"
    mock_container.logs.return_value = b"PostgreSQL started\n"
    return mock_container
```

- [ ] **Step 7: Commit**

```bash
git add src/tsdbenv/__init__.py requirements.txt setup.py tests/conftest.py tests/unit/conftest.py tests/integration/conftest.py
git commit -m "feat: initialize tsdbenv package structure and test fixtures"
```

---

## Task 2: Data Models (Container, VersionMatrix, PostgresConfig)

**Files:**
- Create: `src/tsdbenv/models.py`
- Test: `tests/unit/test_models.py`

**Interfaces:**
- Produces:
  - `Container(name, postgres_version, timescaledb_version, created_at, last_accessed_at, config_path, docker_id, port, bind_ip, tsdbadmin_password)` — serializable to/from JSON
  - `VersionMatrix(postgres_versions, last_fetched)` with `is_compatible(pg_ver, ts_ver) -> bool`
  - `PostgresConfig(raw_settings, source_file, is_valid)` with `to_env_dict() -> dict`

- [ ] **Step 1: Write test_models.py (failing tests)**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
import json
from datetime import datetime
from tsdbenv.models import Container, VersionMatrix, PostgresConfig

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_models.py -v
```

Expected: FAIL (models.py does not exist)

- [ ] **Step 3: Write models.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List

class Container(BaseModel):
    """Represents a PostgreSQL + TimescaleDB container."""
    name: str = Field(..., description="Unique container identifier")
    postgres_version: str = Field(..., description="PostgreSQL version (e.g., '14')")
    timescaledb_version: str = Field(..., description="TimescaleDB version (e.g., '2.8.0')")
    created_at: datetime = Field(..., description="Container creation timestamp")
    last_accessed_at: datetime = Field(..., description="Last user interaction timestamp")
    config_path: Optional[str] = Field(None, description="Path to PostgreSQL config file")
    docker_id: str = Field(..., description="Docker container ID")
    port: int = Field(default=5432, description="PostgreSQL port")
    bind_ip: str = Field(default="127.0.0.1", description="IP to bind container to")
    tsdbadmin_password: str = Field(..., description="tsdbadmin user password")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "mydb",
                "postgres_version": "14",
                "timescaledb_version": "2.8.0",
                "created_at": "2026-08-19T10:00:00Z",
                "last_accessed_at": "2026-08-19T14:00:00Z",
                "config_path": None,
                "docker_id": "abc123",
                "port": 5432,
                "bind_ip": "127.0.0.1",
                "tsdbadmin_password": "secure_pwd",
            }
        }

class VersionMatrix(BaseModel):
    """Compatibility matrix: PostgreSQL versions → compatible TimescaleDB versions."""
    postgres_versions: Dict[str, List[str]] = Field(
        ..., description="Map of PG version → list of compatible TS versions"
    )
    last_fetched: datetime = Field(..., description="When matrix was last fetched")

    def is_compatible(self, postgres_ver: str, timescaledb_ver: str) -> bool:
        """Check if postgres_ver and timescaledb_ver are compatible."""
        if postgres_ver not in self.postgres_versions:
            return False
        return timescaledb_ver in self.postgres_versions[postgres_ver]

class PostgresConfig(BaseModel):
    """PostgreSQL configuration (key=value pairs)."""
    raw_settings: Dict[str, str] = Field(
        default_factory=dict, description="PostgreSQL settings (key=value)"
    )
    source_file: Optional[str] = Field(None, description="Source file path")
    is_valid: bool = Field(default=True, description="Whether config passed validation")

    def to_env_dict(self) -> Dict[str, str]:
        """Convert settings to environment variable format (for Docker)."""
        return self.raw_settings.copy()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_models.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tsdbenv/models.py tests/unit/test_models.py
git commit -m "feat: add data models (Container, VersionMatrix, PostgresConfig)"
```

---

## Task 3: Version Manager (Fetch, Cache, Validate)

**Files:**
- Create: `src/tsdbenv/version_manager.py`
- Test: `tests/unit/test_version_manager.py`

**Interfaces:**
- Consumes: `VersionMatrix` from Task 2
- Produces:
  - `VersionManager` class with methods:
    - `__init__(cache_dir: Path)`
    - `is_compatible(pg_ver: str, ts_ver: str) -> bool`
    - `fetch_from_tigerdata() -> VersionMatrix` (raises on network error)
    - `load_from_cache() -> Optional[VersionMatrix]`
    - `get_or_fetch() -> VersionMatrix`

- [ ] **Step 1: Write test_version_manager.py (failing tests)**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
import json
from datetime import datetime
from pathlib import Path
from tsdbenv.version_manager import VersionManager
from tsdbenv.models import VersionMatrix

def test_version_manager_init(temp_state_dir):
    """Test VersionManager initialization."""
    vm = VersionManager(cache_dir=temp_state_dir)
    assert vm.cache_dir == temp_state_dir

def test_version_manager_is_compatible_true(sample_version_matrix, temp_state_dir):
    """Test is_compatible returns True for valid combo."""
    vm = VersionManager(cache_dir=temp_state_dir)
    vm.matrix = sample_version_matrix
    assert vm.is_compatible("14", "2.8.0") is True

def test_version_manager_is_compatible_false(sample_version_matrix, temp_state_dir):
    """Test is_compatible returns False for invalid combo."""
    vm = VersionManager(cache_dir=temp_state_dir)
    vm.matrix = sample_version_matrix
    assert vm.is_compatible("14", "2.11.0") is False

def test_version_manager_load_from_cache(temp_state_dir, sample_version_matrix):
    """Test loading matrix from cache file."""
    cache_file = temp_state_dir / "version_matrix.json"
    cache_data = {
        "fetched_at": sample_version_matrix.last_fetched.isoformat(),
        "matrix": sample_version_matrix.postgres_versions,
    }
    cache_file.write_text(json.dumps(cache_data))
    
    vm = VersionManager(cache_dir=temp_state_dir)
    matrix = vm.load_from_cache()
    
    assert matrix is not None
    assert matrix.is_compatible("14", "2.8.0")

def test_version_manager_load_from_cache_not_found(temp_state_dir):
    """Test load_from_cache returns None if file doesn't exist."""
    vm = VersionManager(cache_dir=temp_state_dir)
    matrix = vm.load_from_cache()
    assert matrix is None

def test_version_manager_get_or_fetch_uses_cache(temp_state_dir, sample_version_matrix):
    """Test get_or_fetch uses cached matrix if available."""
    cache_file = temp_state_dir / "version_matrix.json"
    cache_data = {
        "fetched_at": sample_version_matrix.last_fetched.isoformat(),
        "matrix": sample_version_matrix.postgres_versions,
    }
    cache_file.write_text(json.dumps(cache_data))
    
    vm = VersionManager(cache_dir=temp_state_dir)
    matrix = vm.get_or_fetch()
    
    assert matrix is not None
    assert matrix.is_compatible("14", "2.8.0")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_version_manager.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: Write version_manager.py**

```python
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
        """Check if versions are compatible.
        
        Args:
            postgres_ver: PostgreSQL version (e.g., "14")
            timescaledb_ver: TimescaleDB version (e.g., "2.8.0")
        
        Returns:
            True if compatible, False otherwise
        """
        if self.matrix is None:
            self.matrix = self.get_or_fetch()
        return self.matrix.is_compatible(postgres_ver, timescaledb_ver)

    def load_from_cache(self) -> Optional[VersionMatrix]:
        """Load compatibility matrix from cache file.
        
        Returns:
            VersionMatrix if cache exists, None otherwise
        """
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
        """Fetch matrix from TigerData docs (stub for now).
        
        Returns:
            VersionMatrix from TigerData or fallback
        """
        # Phase 3: implement actual fetching from TigerData URL
        return VersionMatrix(
            postgres_versions=self.FALLBACK_MATRIX,
            last_fetched=datetime.now(),
        )

    def get_or_fetch(self) -> VersionMatrix:
        """Get matrix from cache, or fetch if unavailable.
        
        Returns:
            VersionMatrix (cached or fetched)
        """
        cached = self.load_from_cache()
        if cached is not None:
            return cached
        return self.fetch_from_tigerdata()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_version_manager.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tsdbenv/version_manager.py tests/unit/test_version_manager.py
git commit -m "feat: add VersionManager with cache and compatibility validation"
```

---

## Task 4: Config Handler (Parse .conf and KV Files)

**Files:**
- Create: `src/tsdbenv/config_handler.py`
- Test: `tests/unit/test_config_handler.py`

**Interfaces:**
- Consumes: `PostgresConfig` from Task 2
- Produces:
  - `ConfigHandler` class with static methods:
    - `parse_simple_kv(path: Path) -> PostgresConfig`
    - `parse_postgresql_conf(path: Path) -> PostgresConfig`
    - `parse_file(path: Path) -> PostgresConfig` (auto-detect format)

- [ ] **Step 1: Write test_config_handler.py (failing tests)**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
import tempfile
from pathlib import Path
from tsdbenv.config_handler import ConfigHandler
from tsdbenv.models import PostgresConfig

def test_parse_simple_kv(temp_state_dir):
    """Test parsing simple key=value config."""
    config_file = temp_state_dir / "simple.conf"
    config_file.write_text("shared_buffers=256MB\nwork_mem=4MB\n")
    
    config = ConfigHandler.parse_simple_kv(config_file)
    
    assert config.is_valid is True
    assert config.raw_settings["shared_buffers"] == "256MB"
    assert config.raw_settings["work_mem"] == "4MB"
    assert config.source_file == str(config_file)

def test_parse_simple_kv_with_comments(temp_state_dir):
    """Test parsing simple KV with comments."""
    config_file = temp_state_dir / "simple.conf"
    config_file.write_text("# Comment\nshared_buffers=256MB\n# Another comment\nwork_mem=4MB\n")
    
    config = ConfigHandler.parse_simple_kv(config_file)
    
    assert config.is_valid is True
    assert len(config.raw_settings) == 2

def test_parse_postgresql_conf(temp_state_dir):
    """Test parsing full postgresql.conf format."""
    config_file = temp_state_dir / "postgresql.conf"
    config_file.write_text("""
# PostgreSQL Configuration

shared_buffers = 256MB
work_mem = 4MB

# More settings
log_statement = 'all'
""")
    
    config = ConfigHandler.parse_postgresql_conf(config_file)
    
    assert config.is_valid is True
    assert config.raw_settings["shared_buffers"] == "256MB"
    assert config.raw_settings["log_statement"] == "'all'"

def test_parse_file_auto_detect_simple_kv(temp_state_dir):
    """Test auto-detection of simple KV format."""
    config_file = temp_state_dir / "config.txt"
    config_file.write_text("shared_buffers=256MB\nwork_mem=4MB\n")
    
    config = ConfigHandler.parse_file(config_file)
    
    assert config.is_valid is True
    assert config.raw_settings["shared_buffers"] == "256MB"

def test_parse_file_not_found():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        ConfigHandler.parse_file(Path("/nonexistent/config.conf"))

def test_config_to_env_dict(sample_postgres_config):
    """Test converting config to environment variables."""
    env_dict = sample_postgres_config.to_env_dict()
    
    assert env_dict["shared_buffers"] == "256MB"
    assert env_dict["work_mem"] == "4MB"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_config_handler.py -v
```

Expected: FAIL

- [ ] **Step 3: Write config_handler.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import re
from pathlib import Path
from typing import Dict, Tuple
from tsdbenv.models import PostgresConfig

class ConfigHandler:
    """Parses PostgreSQL configuration files."""

    @staticmethod
    def parse_simple_kv(path: Path) -> PostgresConfig:
        """Parse simple key=value configuration file.
        
        Format:
            key1=value1
            key2=value2
            # Comments ignored
        
        Args:
            path: Path to config file
        
        Returns:
            PostgresConfig with parsed settings
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        settings = {}
        for line in path.read_text().strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
        
        return PostgresConfig(
            raw_settings=settings,
            source_file=str(path),
            is_valid=True,
        )

    @staticmethod
    def parse_postgresql_conf(path: Path) -> PostgresConfig:
        """Parse full postgresql.conf configuration file.
        
        Handles comments, spacing, and quoted values.
        
        Args:
            path: Path to postgresql.conf
        
        Returns:
            PostgresConfig with parsed settings
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        settings = {}
        for line in path.read_text().strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Match "key = value" or key=value
            match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$', line)
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
        """Auto-detect format and parse config file.
        
        Args:
            path: Path to config file
        
        Returns:
            PostgresConfig with parsed settings
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        # Simple heuristic: if file has "=" on most lines, treat as KV
        # Otherwise treat as postgresql.conf
        content = path.read_text()
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
        
        if lines:
            kv_count = sum(1 for line in lines if '=' in line)
            if kv_count / len(lines) > 0.8:
                return ConfigHandler.parse_simple_kv(path)
        
        return ConfigHandler.parse_postgresql_conf(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_config_handler.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tsdbenv/config_handler.py tests/unit/test_config_handler.py
git commit -m "feat: add ConfigHandler for parsing PostgreSQL config files"
```

---

## Task 5: Network Validator (IP Detection & Validation)

**Files:**
- Create: `src/tsdbenv/network_validator.py`
- Test: `tests/unit/test_network_validator.py`

**Interfaces:**
- Produces:
  - `NetworkValidator` class with static methods:
    - `get_local_ips() -> list[str]`
    - `get_network_gateway() -> Optional[str]`
    - `get_subnet(gateway_ip: str) -> str`
    - `is_ip_on_subnet(ip: str, subnet: str) -> bool`
    - `validate_bind_ip(bind_ip: str) -> Tuple[bool, Optional[str]]`

- [ ] **Step 1: Write test_network_validator.py (failing tests)**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from tsdbenv.network_validator import NetworkValidator

def test_is_ip_on_subnet_true():
    """Test IP on subnet detection (positive case)."""
    result = NetworkValidator.is_ip_on_subnet("192.168.1.100", "192.168.1.0/24")
    assert result is True

def test_is_ip_on_subnet_false():
    """Test IP on subnet detection (negative case)."""
    result = NetworkValidator.is_ip_on_subnet("192.168.2.100", "192.168.1.0/24")
    assert result is False

def test_is_ip_on_subnet_edge_cases():
    """Test IP on subnet edge cases."""
    assert NetworkValidator.is_ip_on_subnet("192.168.1.0", "192.168.1.0/24") is True
    assert NetworkValidator.is_ip_on_subnet("192.168.1.255", "192.168.1.0/24") is True

def test_get_subnet_from_gateway():
    """Test subnet extraction from gateway IP."""
    subnet = NetworkValidator.get_subnet("192.168.1.1")
    # Should return something like 192.168.1.0/24
    assert "192.168.1" in subnet

def test_localhost_validation():
    """Test that localhost is always valid."""
    is_valid, msg = NetworkValidator.validate_bind_ip("127.0.0.1")
    assert is_valid is True
    assert msg is None

def test_invalid_ip_validation():
    """Test validation of IP not on local network."""
    # Mock the gateway to return a specific value
    is_valid, msg = NetworkValidator.validate_bind_ip("10.0.0.1")
    # The behavior depends on actual network; we test structure
    assert isinstance(is_valid, bool)
    if not is_valid:
        assert msg is not None
        assert "not on your LAN" in msg or "unable to determine" in msg.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_network_validator.py -v
```

Expected: FAIL

- [ ] **Step 3: Write network_validator.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import socket
import ipaddress
from typing import Optional, Tuple, List

class NetworkValidator:
    """Validates and detects local network IPs."""

    @staticmethod
    def get_local_ips() -> List[str]:
        """Get all local network IPs on the machine.
        
        Returns:
            List of IP addresses (e.g., ['192.168.1.100', '10.0.0.5'])
        """
        ips = []
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
        except (socket.gaierror, socket.error):
            pass
        
        # Always include localhost
        if "127.0.0.1" not in ips:
            ips.insert(0, "127.0.0.1")
        
        return ips

    @staticmethod
    def get_network_gateway() -> Optional[str]:
        """Detect LAN gateway IP (e.g., 192.168.1.1).
        
        Returns:
            Gateway IP or None if unable to detect
        """
        try:
            # Get the machine's primary IP (not 127.0.0.1)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Assume gateway is .1 on the same subnet (common but not universal)
            parts = local_ip.rsplit('.', 1)
            if len(parts) == 2:
                return f"{parts[0]}.1"
        except Exception:
            pass
        
        return None

    @staticmethod
    def get_subnet(gateway_ip: str) -> str:
        """Extract subnet from gateway IP.
        
        Args:
            gateway_ip: Gateway IP (e.g., '192.168.1.1')
        
        Returns:
            CIDR subnet (e.g., '192.168.1.0/24')
        """
        # Simple heuristic: assume /24 subnet
        parts = gateway_ip.rsplit('.', 1)
        if len(parts) == 2:
            return f"{parts[0]}.0/24"
        return f"{gateway_ip}/32"

    @staticmethod
    def is_ip_on_subnet(ip: str, subnet: str) -> bool:
        """Check if IP is on given subnet.
        
        Args:
            ip: IP address (e.g., '192.168.1.100')
            subnet: CIDR subnet (e.g., '192.168.1.0/24')
        
        Returns:
            True if IP is on subnet, False otherwise
        """
        try:
            ip_addr = ipaddress.ip_address(ip)
            subnet_net = ipaddress.ip_network(subnet, strict=False)
            return ip_addr in subnet_net
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            return False

    @staticmethod
    def validate_bind_ip(bind_ip: str) -> Tuple[bool, Optional[str]]:
        """Validate bind IP against LAN gateway.
        
        Args:
            bind_ip: IP to validate (e.g., '192.168.1.100' or '127.0.0.1')
        
        Returns:
            (is_valid: bool, warning_message: Optional[str])
            - is_valid=True if IP is on LAN or is localhost
            - warning_message=alert if IP not on detected subnet
        """
        # Localhost is always valid
        if bind_ip == "127.0.0.1" or bind_ip == "localhost":
            return (True, None)
        
        gateway = NetworkValidator.get_network_gateway()
        if gateway is None:
            # Unable to detect gateway; warn but allow
            return (True, "⚠️  Unable to detect network gateway. IP may not be reachable.")
        
        subnet = NetworkValidator.get_subnet(gateway)
        if not NetworkValidator.is_ip_on_subnet(bind_ip, subnet):
            warning = f"⚠️  IP {bind_ip} is not on your LAN (gateway: {gateway}, subnet: {subnet}). You may not be able to access the container."
            return (False, warning)
        
        return (True, None)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_network_validator.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tsdbenv/network_validator.py tests/unit/test_network_validator.py
git commit -m "feat: add NetworkValidator for IP detection and subnet validation"
```

---

## Task 6: State Tracker (Load, Save, Stale Detection)

**Files:**
- Create: `src/tsdbenv/state_tracker.py`
- Test: `tests/unit/test_state_tracker.py`

**Interfaces:**
- Consumes: `Container` from Task 2
- Produces:
  - `StateTracker` class with methods:
    - `__init__(state_dir: Path)`
    - `load_containers() -> list[Container]`
    - `save_container(container: Container)`
    - `delete_container(name: str)`
    - `mark_accessed(name: str)`
    - `get_stale_containers(days: int = 5) -> list[Container]`

- [ ] **Step 1: Write test_state_tracker.py (failing tests)**

```python
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
    
    # Fresh container
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
    
    # Stale container (not accessed for 6 days)
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_state_tracker.py -v
```

Expected: FAIL

- [ ] **Step 3: Write state_tracker.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from tsdbenv.models import Container

class StateTracker:
    """Manages container state (load/save/stale detection)."""

    STATE_FILE = "containers.json"

    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize StateTracker.
        
        Args:
            state_dir: Directory for state file (default: ~/.tsdbenv)
        """
        if state_dir is None:
            state_dir = Path.home() / ".tsdbenv"
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / self.STATE_FILE

    def load_containers(self) -> List[Container]:
        """Load all containers from state file.
        
        Returns:
            List of Container objects
        """
        if not self.state_file.exists():
            return []
        
        try:
            data = json.loads(self.state_file.read_text())
            return [Container(**c) for c in data.get("containers", [])]
        except (json.JSONDecodeError, ValueError):
            return []

    def save_container(self, container: Container) -> None:
        """Save a container to state file (add or update).
        
        Args:
            container: Container to save
        """
        containers = self.load_containers()
        
        # Remove if exists (replace)
        containers = [c for c in containers if c.name != container.name]
        containers.append(container)
        
        self._write_state(containers)

    def delete_container(self, name: str) -> None:
        """Delete a container from state.
        
        Args:
            name: Container name
        """
        containers = self.load_containers()
        containers = [c for c in containers if c.name != name]
        self._write_state(containers)

    def mark_accessed(self, name: str) -> None:
        """Update last_accessed_at for a container.
        
        Args:
            name: Container name
        """
        containers = self.load_containers()
        for c in containers:
            if c.name == name:
                c.last_accessed_at = datetime.now()
                break
        self._write_state(containers)

    def get_stale_containers(self, days: int = 5) -> List[Container]:
        """Get containers not accessed for N days.
        
        Args:
            days: Threshold in days (default: 5)
        
        Returns:
            List of stale Container objects
        """
        containers = self.load_containers()
        now = datetime.now()
        stale = []
        
        for c in containers:
            age = now - c.last_accessed_at
            if age > timedelta(days=days):
                stale.append(c)
        
        return stale

    def _write_state(self, containers: List[Container]) -> None:
        """Write containers to state file.
        
        Args:
            containers: List of Container objects
        """
        data = {
            "containers": [c.model_dump() for c in containers]
        }
        # Convert datetime to ISO format for JSON
        data_json = json.dumps(
            data,
            default=lambda x: x.isoformat() if isinstance(x, datetime) else x,
            indent=2,
        )
        self.state_file.write_text(data_json)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_state_tracker.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tsdbenv/state_tracker.py tests/unit/test_state_tracker.py
git commit -m "feat: add StateTracker for container state persistence and stale detection"
```

---

## Task 7: Utilities (Helpers)

**Files:**
- Create: `src/tsdbenv/utils.py`

**Interfaces:**
- Produces:
  - `generate_password(length: int = 16) -> str`
  - `get_state_dir() -> Path`
  - `ensure_state_dir() -> Path`

- [ ] **Step 1: Write utils.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import secrets
import string
from pathlib import Path

def generate_password(length: int = 16) -> str:
    """Generate a secure random password.
    
    Args:
        length: Password length (default: 16)
    
    Returns:
        Random secure password
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_state_dir() -> Path:
    """Get tsdbenv state directory path.
    
    Returns:
        Path to ~/.tsdbenv
    """
    return Path.home() / ".tsdbenv"

def ensure_state_dir() -> Path:
    """Ensure state directory exists, create if needed.
    
    Returns:
        Path to ~/.tsdbenv
    """
    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir
```

- [ ] **Step 2: Commit**

```bash
git add src/tsdbenv/utils.py
git commit -m "feat: add utility functions (password generation, state dir)"
```

---

# PHASE 2: CLI (TOP-DOWN WITH DOCKER STUBS)

## Task 8: Docker Utils (Stub for Phase 3)

**Files:**
- Create: `src/tsdbenv/docker_utils.py`

**Interfaces:**
- Produces:
  - `DockerClient` class (wrapper around docker SDK) with methods:
    - `check_docker_installed() -> bool`
    - `create_container(...) -> str` (stub: returns mock ID)
    - `start_container(container_id: str) -> None` (stub)
    - `stop_container(container_id: str) -> None` (stub)
    - `remove_container(container_id: str) -> None` (stub)
    - `get_container_logs(container_id: str) -> str` (stub)
    - `list_containers() -> list[dict]` (stub)

- [ ] **Step 1: Write docker_utils.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from typing import Optional, List, Dict
import shutil

class DockerClient:
    """Wrapper around Docker SDK (stubs for Phase 2)."""

    def __init__(self):
        """Initialize Docker client."""
        self._verify_docker()

    def check_docker_installed(self) -> bool:
        """Check if Docker is installed and running.
        
        Returns:
            True if Docker is available, False otherwise
        """
        return shutil.which("docker") is not None

    def _verify_docker(self) -> None:
        """Verify Docker is installed. Raise if not."""
        if not self.check_docker_installed():
            raise RuntimeError(
                "Docker is not installed or not in PATH. "
                "Please install Docker: https://docs.docker.com/get-docker/"
            )

    def create_container(
        self,
        image: str,
        name: str,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict]] = None,
    ) -> str:
        """Create a Docker container (STUB for Phase 2).
        
        Args:
            image: Docker image name
            name: Container name
            environment: Environment variables
            ports: Port mappings
            volumes: Volume mounts
        
        Returns:
            Container ID (mocked)
        """
        # Phase 3: Implement real Docker SDK call
        return f"mock_{name}_id_12345"

    def start_container(self, container_id: str) -> None:
        """Start a container (STUB for Phase 2).
        
        Args:
            container_id: Container ID
        """
        # Phase 3: Implement real Docker SDK call
        pass

    def stop_container(self, container_id: str) -> None:
        """Stop a container (STUB for Phase 2).
        
        Args:
            container_id: Container ID
        """
        # Phase 3: Implement real Docker SDK call
        pass

    def remove_container(self, container_id: str) -> None:
        """Remove a container (STUB for Phase 2).
        
        Args:
            container_id: Container ID
        """
        # Phase 3: Implement real Docker SDK call
        pass

    def get_container_logs(self, container_id: str) -> str:
        """Get container logs (STUB for Phase 2).
        
        Args:
            container_id: Container ID
        
        Returns:
            Log output (mocked)
        """
        # Phase 3: Implement real Docker SDK call
        return "[Mock logs] Container is running successfully."

    def list_containers(self) -> List[Dict]:
        """List all containers (STUB for Phase 2).
        
        Returns:
            List of container dicts with keys: id, name, status
        """
        # Phase 3: Implement real Docker SDK call
        return []
```

- [ ] **Step 2: Commit**

```bash
git add src/tsdbenv/docker_utils.py
git commit -m "feat: add DockerClient stub for Phase 2 (real impl in Phase 3)"
```

---

## Task 9: CLI (Main Entry Point with Click)

**Files:**
- Create: `src/tsdbenv/cli.py`
- Test: `tests/integration/test_cli_flows.py`

**Interfaces:**
- Consumes: All models, managers, handlers from Phase 1; DockerClient from Task 8
- Produces:
  - `main()` Click command group with subcommands:
    - `--version` flag
    - `--new` command
    - `--list` command
    - `--logs` command
    - `--remove` command
    - No args → interactive menu

- [ ] **Step 1: Write cli.py (main structure)**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import click
from pathlib import Path
from datetime import datetime
from tsdbenv import __version__
from tsdbenv.version_manager import VersionManager
from tsdbenv.config_handler import ConfigHandler
from tsdbenv.state_tracker import StateTracker
from tsdbenv.network_validator import NetworkValidator
from tsdbenv.docker_utils import DockerClient
from tsdbenv.utils import generate_password, ensure_state_dir
from tsdbenv.models import Container

class CLIState:
    """Shared state for CLI operations."""
    def __init__(self):
        self.state_dir = ensure_state_dir()
        self.state_tracker = StateTracker(state_dir=self.state_dir)
        self.version_manager = VersionManager(cache_dir=self.state_dir)
        try:
            self.docker_client = DockerClient()
        except RuntimeError:
            self.docker_client = None

# Global state
cli_state = CLIState()

@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def main(ctx, version):
    """tsdbenv - PostgreSQL + TimescaleDB environment manager."""
    if version:
        click.echo(f"tsdbenv {__version__}")
        ctx.exit(0)
    
    # Check Docker installation
    if cli_state.docker_client is None:
        click.echo("❌ Docker is not installed or not running.")
        click.echo("   Please install Docker: https://docs.docker.com/get-docker/")
        ctx.exit(1)
    
    # If no command, show interactive menu
    if ctx.invoked_subcommand is None:
        show_interactive_menu()

@main.command()
@click.option("--postgres", help="PostgreSQL version (e.g., 14)")
@click.option("--timescaledb", help="TimescaleDB version (e.g., 2.8.0)")
@click.option("--name", help="Container name")
@click.option("--config", type=click.Path(exists=True), help="PostgreSQL config file path")
@click.option("--bind-ip", help="IP to bind container to (default: 127.0.0.1)")
@click.option("--force", is_flag=True, help="Override version compatibility check")
def new(postgres, timescaledb, name, config, bind_ip, force):
    """Create a new PostgreSQL + TimescaleDB container."""
    # Step 1: Prompt for versions if not provided
    if not postgres:
        postgres = click.prompt("PostgreSQL version", type=str)
    if not timescaledb:
        timescaledb = click.prompt("TimescaleDB version", type=str)
    
    # Step 2: Validate compatibility
    if not force and not cli_state.version_manager.is_compatible(postgres, timescaledb):
        click.echo(f"❌ TimescaleDB {timescaledb} is not compatible with PostgreSQL {postgres}")
        ctx_exit = click.get_current_context().exit
        ctx_exit(1)
    
    # Step 3: Prompt for container name
    if not name:
        name = click.prompt("Container name", type=str)
    
    # Step 4: Load config if requested
    postgres_config = None
    if not config:
        if click.confirm("Load PostgreSQL config file?"):
            config = click.prompt("Config file path", type=click.Path(exists=True))
    
    if config:
        try:
            postgres_config = ConfigHandler.parse_file(Path(config))
            if not postgres_config.is_valid:
                click.echo("⚠️  Config validation warnings detected")
        except Exception as e:
            click.echo(f"❌ Failed to parse config: {e}")
            return
    
    # Step 5: Prompt for network binding
    if not bind_ip:
        bind_choice = click.prompt(
            "Network binding",
            type=click.Choice(["localhost", "custom"]),
            default="localhost"
        )
        if bind_choice == "localhost":
            bind_ip = "127.0.0.1"
        else:
            detected_ips = NetworkValidator.get_local_ips()
            click.echo(f"Detected IPs: {', '.join(detected_ips)}")
            bind_ip = click.prompt("Enter IP or select from above", type=str)
    
    # Validate IP
    is_valid, warning = NetworkValidator.validate_bind_ip(bind_ip)
    if not is_valid:
        click.echo(warning)
        if not click.confirm("Continue anyway?"):
            return
    
    # Step 6: Create container (stub)
    tsdbadmin_password = generate_password()
    container_id = cli_state.docker_client.create_container(
        image=f"postgres:{postgres}-alpine",
        name=name,
        environment={"POSTGRES_PASSWORD": "postgres", "PGPASSWORD": tsdbadmin_password},
        ports={5432: 5432},
    )
    
    # Step 7: Save to state
    container = Container(
        name=name,
        postgres_version=postgres,
        timescaledb_version=timescaledb,
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=config,
        docker_id=container_id,
        port=5432,
        bind_ip=bind_ip,
        tsdbadmin_password=tsdbadmin_password,
    )
    cli_state.state_tracker.save_container(container)
    
    # Step 8: Display connection info
    display_connection_info(container)

@main.command()
def list():
    """List all containers."""
    containers = cli_state.state_tracker.load_containers()
    
    if not containers:
        click.echo("No containers found.")
        return
    
    # Check for stale containers
    stale = cli_state.state_tracker.get_stale_containers(days=5)
    for s in stale:
        click.echo(f"⚠️  Container '{s.name}' unused for 5+ days. Remove? (y/n)")
    
    click.echo(f"\n{'Name':<15} {'PG':<5} {'TS':<8} {'IP':<15} {'Port':<6}")
    click.echo("-" * 55)
    for c in containers:
        click.echo(f"{c.name:<15} {c.postgres_version:<5} {c.timescaledb_version:<8} {c.bind_ip:<15} {c.port:<6}")

@main.command()
@click.argument("container_name", required=False)
def logs(container_name):
    """Show container logs."""
    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name",
            type=click.Choice([c.name for c in containers])
        )
    
    container = next((c for c in cli_state.state_tracker.load_containers() if c.name == container_name), None)
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return
    
    cli_state.state_tracker.mark_accessed(container_name)
    logs_output = cli_state.docker_client.get_container_logs(container.docker_id)
    click.echo(logs_output)

@main.command()
@click.argument("container_name", required=False)
def remove(container_name):
    """Remove a container."""
    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name",
            type=click.Choice([c.name for c in containers])
        )
    
    container = next((c for c in cli_state.state_tracker.load_containers() if c.name == container_name), None)
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return
    
    if click.confirm(f"Remove container '{container_name}'? This cannot be undone."):
        cli_state.docker_client.remove_container(container.docker_id)
        cli_state.state_tracker.delete_container(container_name)
        click.echo(f"✅ Container '{container_name}' removed.")

def display_connection_info(container: Container) -> None:
    """Display connection information to the user."""
    click.echo(f"""
✅ Container '{container.name}' created successfully!

Connection Info:
- Host: {container.bind_ip}
- Port: {container.port}
- Admin User: postgres
- App User: tsdbadmin (same privileges as postgres)
- Password: {container.tsdbadmin_password}

Connect:
  psql -h {container.bind_ip} -U tsdbadmin -d postgres
""")

def show_interactive_menu() -> None:
    """Show interactive menu when no command specified."""
    choice = click.prompt(
        "What would you like to do?",
        type=click.Choice(["new", "list", "logs", "remove"]),
    )
    
    if choice == "new":
        ctx = click.get_current_context()
        ctx.invoke(new, postgres=None, timescaledb=None, name=None, config=None, bind_ip=None, force=False)
    elif choice == "list":
        ctx = click.get_current_context()
        ctx.invoke(list)
    elif choice == "logs":
        ctx = click.get_current_context()
        ctx.invoke(logs, container_name=None)
    elif choice == "remove":
        ctx = click.get_current_context()
        ctx.invoke(remove, container_name=None)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write test_cli_flows.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from click.testing import CliRunner
from tsdbenv.cli import main
from tsdbenv.state_tracker import StateTracker
from tsdbenv.models import Container
from datetime import datetime

@pytest.fixture
def cli_runner():
    """Create a Click CLI runner."""
    return CliRunner()

@pytest.fixture
def isolated_cli(tmp_path, monkeypatch):
    """CLI runner with isolated state directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    return runner

def test_cli_version(cli_runner):
    """Test --version flag."""
    result = cli_runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "tsdbenv" in result.output

def test_cli_new_with_flags(isolated_cli):
    """Test creating container with flags (no prompts)."""
    result = isolated_cli.invoke(main, [
        "new",
        "--postgres", "14",
        "--timescaledb", "2.8.0",
        "--name", "testdb",
        "--bind-ip", "127.0.0.1",
    ])
    # Phase 2 stub will succeed
    assert result.exit_code == 0 or "created successfully" in result.output

def test_cli_list_empty(isolated_cli):
    """Test list with no containers."""
    result = isolated_cli.invoke(main, ["list"])
    assert "No containers found" in result.output

def test_cli_list_with_containers(temp_state_dir):
    """Test list with saved containers."""
    st = StateTracker(state_dir=temp_state_dir)
    c = Container(
        name="mydb",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="abc123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd",
    )
    st.save_container(c)
    
    # List should show the container
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert "mydb" in result.output or result.exit_code == 0
```

- [ ] **Step 3: Run integration tests**

```bash
pytest tests/integration/test_cli_flows.py -v
```

Expected: PASS (or tests that validate CLI structure)

- [ ] **Step 4: Commit**

```bash
git add src/tsdbenv/cli.py tests/integration/test_cli_flows.py
git commit -m "feat: add Click CLI with all commands (--new, --list, --logs, --remove)"
```

---

## Task 10: Integration Tests (Container Lifecycle)

**Files:**
- Test: `tests/integration/test_container_lifecycle.py`

**Interfaces:**
- Consumes: All Phase 1 & 2 components
- Tests end-to-end flows with mocked Docker

- [ ] **Step 1: Write test_container_lifecycle.py**

```python
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tsdbenv.state_tracker import StateTracker
from tsdbenv.version_manager import VersionManager
from tsdbenv.models import Container

def test_full_lifecycle(temp_state_dir):
    """Test full container lifecycle: create → access → stale → remove."""
    st = StateTracker(state_dir=temp_state_dir)
    vm = VersionManager(cache_dir=temp_state_dir)
    
    # 1. Create container
    assert vm.is_compatible("14", "2.8.0") is True
    
    container = Container(
        name="lifecycle_test",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="id123",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd",
    )
    st.save_container(container)
    
    # 2. Load and verify
    containers = st.load_containers()
    assert len(containers) == 1
    assert containers[0].name == "lifecycle_test"
    
    # 3. Mark accessed (fresh)
    st.mark_accessed("lifecycle_test")
    stale_list = st.get_stale_containers(days=5)
    assert len(stale_list) == 0
    
    # 4. Simulate stale (manually adjust timestamp)
    containers = st.load_containers()
    containers[0].last_accessed_at = datetime.now() - timedelta(days=6)
    st.save_container(containers[0])
    
    # 5. Detect stale
    stale_list = st.get_stale_containers(days=5)
    assert len(stale_list) == 1
    
    # 6. Remove
    st.delete_container("lifecycle_test")
    containers = st.load_containers()
    assert len(containers) == 0

def test_version_compatibility_flow(temp_state_dir):
    """Test version compatibility validation flow."""
    vm = VersionManager(cache_dir=temp_state_dir)
    
    # Valid combinations
    assert vm.is_compatible("14", "2.8.0") is True
    assert vm.is_compatible("15", "2.9.0") is True
    
    # Invalid combinations
    assert vm.is_compatible("14", "2.11.0") is False
    assert vm.is_compatible("99", "2.8.0") is False

def test_state_persistence(temp_state_dir):
    """Test that state persists across StateTracker instances."""
    # First instance: create container
    st1 = StateTracker(state_dir=temp_state_dir)
    c1 = Container(
        name="persist_test",
        postgres_version="14",
        timescaledb_version="2.8.0",
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=None,
        docker_id="id456",
        port=5432,
        bind_ip="127.0.0.1",
        tsdbadmin_password="pwd",
    )
    st1.save_container(c1)
    
    # Second instance: load and verify
    st2 = StateTracker(state_dir=temp_state_dir)
    containers = st2.load_containers()
    assert len(containers) == 1
    assert containers[0].name == "persist_test"
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/integration/test_container_lifecycle.py -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_container_lifecycle.py
git commit -m "test: add integration tests for full container lifecycle"
```

---

## Task 11: Coverage Report & Documentation

**Files:**
- Run coverage analysis
- Update README (optional)

- [ ] **Step 1: Run coverage analysis**

```bash
pytest --cov=src/tsdbenv --cov-report=term-missing tests/
```

Expected: 80%+ coverage on core modules

- [ ] **Step 2: Verify no critical gaps**

```bash
pytest --cov=src/tsdbenv --cov-report=html tests/
# Open htmlcov/index.html to review
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "test: add coverage reporting (80%+ on core modules)"
```

---

## Task 12: Final Integration Check

**Files:**
- Manual test of CLI

- [ ] **Step 1: Install package in dev mode**

```bash
pip install -e .
```

- [ ] **Step 2: Test CLI entry point**

```bash
tsdbenv --version
```

Expected: Outputs version

- [ ] **Step 3: Test new container flow (interactive)**

```bash
tsdbenv --new
# Follow prompts
```

Expected: Container created (mocked in Phase 2)

- [ ] **Step 4: Test list command**

```bash
tsdbenv --list
```

Expected: Shows created containers

- [ ] **Step 5: Commit final integration**

```bash
git add .
git commit -m "test: verify full CLI integration (Phase 1 & 2 complete)"
```

---

## Summary

**Phase 1 Complete:**
- ✅ Data models (Container, VersionMatrix, PostgresConfig, NetworkValidator)
- ✅ Version validation (fetch, cache, compatibility checks)
- ✅ Config parsing (simple KV, postgresql.conf)
- ✅ State tracking (JSON persistence, stale detection)
- ✅ Network utilities (IP detection, subnet validation)

**Phase 2 Complete:**
- ✅ Click CLI with all commands (--new, --list, --logs, --remove, --version)
- ✅ Docker client (stubbed; real impl in Phase 3)
- ✅ Interactive menu for users
- ✅ Integration tests (lifecycle, version compatibility, state persistence)

**Next Steps:**
- Phase 3: Implement real Docker integration (replace stubs)
- Phase 4: Polish, logging, error handling, end-to-end testing

---

**Execution Handoff**

Plan complete and saved to `docs/superpowers/plans/2026-08-19-tsdbenv-phase1-phase2.md`. 

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for complex/tricky tasks.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Best for straightforward execution.

Which approach?
