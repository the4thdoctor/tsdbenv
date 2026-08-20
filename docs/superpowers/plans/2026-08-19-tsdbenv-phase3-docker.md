# tsdbenv Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Docker SDK stubs with real implementations, enabling tsdbenv to actually build and manage PostgreSQL + TimescaleDB containers.

**Architecture:** Phase 2's stubs return mock responses; Phase 3 integrates the real `docker` Python SDK to create Dockerfiles, build images, and manage container lifecycle with full Docker operations.

**Tech Stack:** Python 3.8+, docker SDK, pydantic, click, pytest

## Global Constraints

- **Language:** Python 3.8+
- **Authored by:** Wagner Bianchi <wagnerbianchijr@gmail.com>
- **Commit format:** No co-authors; author only
- **File signatures:** Every `.py` file must include header with author, email, and date written (YYYY-MM-DD)
- **Docker:** SDK integration for container management (docker-py library already in requirements)
- **Base branch:** main
- **Coverage target:** 80%+ on core modules

---

## File Structure

### New/Modified Files

```
src/tsdbenv/
├── docker_utils.py          # REPLACE stubs with real Docker SDK calls
├── dockerfiles/
│   └── Dockerfile           # PostgreSQL + TimescaleDB image definition
└── scripts/
    └── init-tsdbadmin.sql   # SQL script to create tsdbadmin user

tests/
├── unit/
│   └── test_docker_utils.py # NEW: Unit tests for Docker operations (with mocks)
└── integration/
    └── test_docker_real.py  # NEW: Real Docker integration tests (requires Docker)
```

---

## Phase 3 Tasks

### Task 1: Dockerfile & Build Script

**Files:**
- Create: `src/tsdbenv/dockerfiles/Dockerfile`
- Create: `src/tsdbenv/scripts/init-tsdbadmin.sql`

**Dockerfile Spec:**
- Base: `postgres:X.X-alpine` (parameterized by PostgreSQL version)
- Install: TimescaleDB extension (from official repos)
- Create: `tsdbadmin` superuser (via init script)
- Expose: Port 5432
- Set: default environment variables for postgres user

**init-tsdbadmin.sql:**
```sql
-- Create tsdbadmin user as superuser (same as postgres)
CREATE ROLE tsdbadmin WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD :password;
-- Set default search_path for tsdbadmin
ALTER ROLE tsdbadmin SET search_path = public, pg_catalog;
```

**Steps:**
1. Write Dockerfile (parameterized for PG versions 14, 15, 16)
2. Write init-tsdbadmin.sql
3. Test: Build image locally with `docker build -t tsdbenv:test-14 --build-arg PG_VERSION=14 .`
4. Commit: "feat: add Dockerfile and init script for PostgreSQL + TimescaleDB"

---

### Task 2: Replace Docker SDK Stubs

**File:**
- Modify: `src/tsdbenv/docker_utils.py` (replace all stub methods)

**Methods to Implement:**

```python
class DockerClient:
    def __init__(self):
        """Initialize real Docker client."""
        self.client = docker.from_env()
        self._verify_docker()
    
    def check_docker_installed(self) -> bool:
        """Check Docker daemon is running."""
        # Try to ping Docker; return True if successful
    
    def create_container(self, image, name, environment, ports, volumes=None) -> str:
        """Create and run a PostgreSQL + TimescaleDB container."""
        # 1. Build image: f"postgres:PG_VERSION-alpine"
        # 2. Create container with environment, ports, volumes
        # 3. Mount init script to /docker-entrypoint-initdb.d/
        # 4. Run container
        # 5. Wait for postgres to be ready (health check)
        # 6. Return container ID
    
    def start_container(self, container_id: str) -> None:
        """Start a stopped container."""
    
    def stop_container(self, container_id: str) -> None:
        """Gracefully stop a running container."""
    
    def remove_container(self, container_id: str) -> None:
        """Remove a container (stop if running first)."""
    
    def get_container_logs(self, container_id: str) -> str:
        """Get container logs (stdout/stderr)."""
    
    def list_containers(self) -> List[Dict]:
        """List all containers (running + stopped)."""
        # Return: [{id, name, status, ports}, ...]
    
    def wait_for_postgres(self, container_id: str, timeout: int = 30) -> bool:
        """Wait for PostgreSQL to be ready for connections."""
        # Poll container logs or use docker health check
```

**Health Check Implementation:**
- Modify Dockerfile to include HEALTHCHECK (psql -U postgres -c "SELECT 1")
- Or poll container.logs() for "database system is ready to accept connections"

**Steps:**
1. Implement real Docker SDK calls (replace stubs)
2. Add health check polling
3. Error handling for Docker daemon issues, port conflicts, etc.
4. Test: `docker ps` output shows created containers
5. Commit: "feat: implement real Docker SDK integration"

---

### Task 3: Create tsdbadmin User in Container

**File:**
- Modify: `src/tsdbenv/docker_utils.py` (in create_container method)

**Implementation:**
- Copy `init-tsdbadmin.sql` to container's `/docker-entrypoint-initdb.d/`
- Docker will execute all `.sql` files in that directory on startup
- Pass tsdbadmin password via environment variable or SQL substitution

**Steps:**
1. Modify Dockerfile to use environment variable for password
2. Pass password to container via environment
3. Verify tsdbadmin is created: `psql -U tsdbadmin -c "SELECT 1"`
4. Commit: "feat: auto-create tsdbadmin user on container startup"

---

### Task 4: Container Lifecycle with Real Docker

**File:**
- Modify: `src/tsdbenv/docker_utils.py`

**Methods:**
- `start_container()` — use `docker.containers.get(id).start()`
- `stop_container()` — use `docker.containers.get(id).stop(timeout=10)`
- `remove_container()` — stop first, then `docker.containers.get(id).remove()`
- `list_containers()` — use `docker.containers.list(all=True)`, extract metadata
- `get_container_logs()` — use `docker.containers.get(id).logs()`

**Error Handling:**
- Docker daemon not running → ConnectionError → user-friendly message
- Container not found → NoSuchContainer → "Container not found"
- Port already in use → APIError → "Port already in use; try different port"

**Steps:**
1. Implement all lifecycle methods
2. Add error handling with user-friendly messages
3. Test: Create, list, logs, stop, remove a real container
4. Commit: "feat: implement full container lifecycle (start, stop, remove, logs)"

---

### Task 5: Unit Tests (Docker Operations with Mocks)

**File:**
- Create: `tests/unit/test_docker_utils.py`

**Mock Docker SDK:**
```python
@pytest.fixture
def mock_docker_client(monkeypatch):
    """Mock docker.from_env()."""
    with patch('docker.from_env') as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        yield mock_client
```

**Test Cases:**
- `test_docker_init_success` — Docker daemon reachable
- `test_docker_init_failure` — Docker not running; raises RuntimeError
- `test_create_container` — Returns container ID; mocked container created
- `test_start_container` — Calls container.start()
- `test_stop_container` — Calls container.stop()
- `test_remove_container` — Stops then removes
- `test_list_containers` — Returns list of container dicts
- `test_get_logs` — Returns log string
- `test_wait_for_postgres_success` — Health check passes within timeout
- `test_wait_for_postgres_timeout` — Health check fails; raises TimeoutError

**Steps:**
1. Write 10+ unit tests with mocked Docker
2. Run: `pytest tests/unit/test_docker_utils.py -v` (expect 10+ pass)
3. Commit: "test: add unit tests for Docker operations (mocked)"

---

### Task 6: Integration Tests (Real Docker)

**File:**
- Create: `tests/integration/test_docker_real.py`

**Mark as Conditional (skip if Docker not available):**
```python
pytest.mark.skipif(
    not docker_available(),
    reason="Docker not available"
)
```

**Real Docker Tests:**
- `test_create_real_container` — Create, verify running, remove
- `test_container_port_mapping` — Verify port accessible
- `test_tsdbadmin_user_exists` — Connect as tsdbadmin, run SELECT 1
- `test_version_matrix_compatibility` — Create container with various PG/TS versions

**Steps:**
1. Write 5+ integration tests
2. Skip tests gracefully if Docker unavailable
3. Run: `pytest tests/integration/test_docker_real.py -v` (skipped or passing)
4. Commit: "test: add integration tests with real Docker (conditional)"

---

### Task 7: CLI Integration with Real Docker

**File:**
- Modify: `src/tsdbenv/cli.py` (no changes needed; CLI already calls docker_utils)

**Verification:**
- CLI uses real Docker now (no code changes needed)
- Test: `python3 -m tsdbenv new --postgres 14 --timescaledb 2.8.0 --name test-real`
- Verify: `docker ps` shows the running container
- Verify: Can connect: `psql -h 127.0.0.1 -U tsdbadmin -d postgres`

**Steps:**
1. Test CLI commands end-to-end
2. Verify container is created and running
3. Verify tsdbadmin can connect
4. Commit: "test: verify CLI works with real Docker"

---

### Task 8: Coverage & Final Integration

**Files:**
- Run coverage report
- Verify 80%+ on docker_utils.py, cli.py

**Steps:**
1. Run: `pytest --cov=src/tsdbenv --cov-report=term-missing tests/`
2. Verify 80%+ coverage (docker_utils should have >90%)
3. Commit: "test: verify Phase 3 coverage (80%+)"

---

### Task 9: Phase 3 Documentation

**Files:**
- Create: `docs/PHASE3.md` (Phase 3 design summary)

**Steps:**
2. Write PHASE3.md summary
3. Commit: "docs: add Phase 3 documentation"

---

## Success Criteria

- ✅ Dockerfile builds PostgreSQL + TimescaleDB images
- ✅ `create_container()` actually creates Docker containers
- ✅ `start_container()`, `stop_container()`, `remove_container()` work with real Docker
- ✅ `list_containers()` shows real containers
- ✅ `get_container_logs()` returns real logs
- ✅ tsdbadmin user created automatically on container startup
- ✅ Health check validates PostgreSQL is ready
- ✅ CLI creates real containers via `tsdbenv new`
- ✅ 80%+ test coverage on docker_utils
- ✅ Integration tests pass (if Docker available)
- ✅ All 9 tasks committed with proper signatures

---

## Testing Strategy

**Unit Tests (Mocked Docker):**
- Fast, no Docker required
- Mock docker.from_env() and container objects
- 10+ test cases covering all methods

**Integration Tests (Real Docker):**
- Require Docker running
- Skip gracefully if unavailable
- 5+ test cases covering full workflows

**Manual Testing:**
```bash
# Create container
python3 -m tsdbenv new --postgres 14 --timescaledb 2.8.0 --name test-phase3

# List containers
python3 -m tsdbenv list

# Connect to container
psql -h 127.0.0.1 -U tsdbadmin -d postgres -c "SELECT version();"

# View logs
python3 -m tsdbenv logs test-phase3

# Stop and remove
python3 -m tsdbenv remove test-phase3
```

---

## Out of Scope (Phase 4)

- Container persistence across CLI runs (we have state tracking, but no volume management yet)
- Backup/restore workflows
- Custom Docker networks (currently bridge only)
- Multi-service orchestration (PostgreSQL + TimescaleDB only for now)
- Kubernetes integration

---

**Document Status:** Ready for implementation  
**Next Step:** Invoke `superpowers:subagent-driven-development` to execute Phase 3 tasks
