# tsdbenv Architecture & Design Specification

**Date:** 2026-08-19  
**Project:** tsdbenv — PostgreSQL + TimescaleDB Environment Manager  
**Repository:** https://github.com/wagnerbianchijr/tsdbenv.git

---

## 1. Overview

tsdbenv is a Python CLI tool managing isolated PostgreSQL + TimescaleDB Docker containers. Users specify PostgreSQL and TimescaleDB versions; tsdbenv validates compatibility, builds containers with optional PostgreSQL configuration, manages lifecycle (create, list, stop, remove, logs), and tracks container state to detect and warn about unused instances.

**Core Goals:**
- Streamlined version compatibility validation
- User-friendly container lifecycle management
- Lightweight state tracking (no external dependencies)
- Support both interactive prompts and automation via flags

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────┐
│  CLI / User Interaction Layer              │
│  (prompts, flags, input validation)        │
├────────────────────────────────────────────┤
│  Container Manager                          │
│  (Docker lifecycle: create, list, stop,    │
│   remove, logs)                            │
├────────────────────────────────────────────┤
│  Config Handler                             │
│  (Parse PostgreSQL .conf & key=value files)│
├────────────────────────────────────────────┤
│  Version Manager                            │
│  (Fetch & validate PG/TimescaleDB matrix)  │
├────────────────────────────────────────────┤
│  State Tracker                              │
│  (Track containers, detect stale 5d+)      │
├────────────────────────────────────────────┤
│  Models & Utilities                         │
│  (Data classes, Docker SDK wrapper, JSON)  │
└────────────────────────────────────────────┘
```

**Design Principle:** Top layer orchestrates; lower layers have no dependencies upward. CLI is thin. Each component has one clear responsibility and is testable in isolation.

---

## 3. Data Models

All models use `pydantic` for validation and `dataclasses` for serialization.

### Container
```python
class Container:
    name: str                           # Unique identifier
    postgres_version: str               # e.g., "14"
    timescaledb_version: str            # e.g., "2.8.0"
    created_at: datetime                # Creation timestamp
    last_accessed_at: datetime          # Last user interaction
    config_path: Optional[str]          # Path to PostgreSQL config file
    docker_id: str                      # Docker container ID
    port: int                           # Mapped PostgreSQL port (default: 5432)
    bind_ip: str                        # Bind IP ("127.0.0.1" for localhost, or network IP)
    tsdbadmin_password: str             # tsdbadmin user password (auto-generated or user-provided)
```

Responsibility: Represent a running/stopped container; serialize to/from JSON; validate version strings. Tracks connection details (port, bind IP, tsdbadmin credentials) for easy user access.

### VersionMatrix
```python
class VersionMatrix:
    postgres_versions: dict[str, list[str]]  # "14" → ["2.8.0", "2.9.0", ...]
    last_fetched: datetime                    # When matrix was fetched
    
    def is_compatible(pg_ver: str, ts_ver: str) -> bool
    def fetch_from_tigerdata() -> None
    def load_from_cache() -> None
```

Responsibility: Load & cache PostgreSQL × TimescaleDB compatibility mappings; provide validation method; fetch from https://www.tigerdata.com/docs/get-started/timescaledb-supported-platforms#postgresql-timescaledb-support-matrix on demand or at startup.

### PostgresConfig
```python
class PostgresConfig:
    raw_settings: dict[str, str]        # key → value pairs
    source_file: Optional[str]          # Path to source file
    is_valid: bool                      # Validation flag
    
    def parse_simple_kv(path: str) -> PostgresConfig
    def parse_postgresql_conf(path: str) -> PostgresConfig
    def to_env_dict() -> dict[str, str]
```

Responsibility: Parse both simple key=value files and full PostgreSQL `.conf` files; validate syntax; convert to environment variables or Docker config mount.

### NetworkValidator (Utility)
```python
class NetworkValidator:
    @staticmethod
    def get_local_ips() -> list[str]
        # Detect all local network IPs on user's machine
    
    @staticmethod
    def get_network_gateway() -> Optional[str]
        # Detect LAN gateway IP (e.g., 192.168.1.1)
    
    @staticmethod
    def get_subnet(gateway_ip: str) -> str
        # Extract subnet from gateway (e.g., 192.168.1.0/24)
    
    @staticmethod
    def is_ip_on_subnet(ip: str, subnet: str) -> bool
        # Check if IP is on same subnet as gateway
    
    @staticmethod
    def validate_bind_ip(bind_ip: str) -> (bool, Optional[str])
        # Returns (is_valid, warning_message)
        # is_valid: True if IP is on LAN or is localhost
        # warning_message: alert if IP is not on detected subnet
```

Responsibility: Detect local network IPs, validate user-provided bind IP against LAN gateway, provide actionable warnings if IP is unreachable.

---

## 4. User Interaction Flow (CLI)

### Command Structure
```bash
tsdbenv --version                      # Show version
tsdbenv --new                          # New container flow (prompts for versions)
tsdbenv --new --postgres 14 --timescaledb 2.8.0  # Skip version prompts
tsdbenv --list                         # List all containers
tsdbenv --logs <container_name>        # Show container logs
tsdbenv --remove <container_name>      # Remove container
tsdbenv                                # No args → interactive menu
```

### Main Flow (Interactive)

1. **Check Docker Installation**
   - If Docker daemon not running or not installed, prompt user and exit with instructions

2. **Stale Detection** (always runs first)
   - Load containers from JSON state
   - For each container: if `now() - last_accessed_at > 5 days`, flag it
   - Prompt user to remove each stale container (optional)

3. **New Container or Manage Existing?**
   - If `--new` flag or user chooses "new":
     - Prompt PostgreSQL version (if not `--postgres`)
     - Prompt TimescaleDB version (if not `--timescaledb`)
     - Validate compatibility; alert if mismatch
     - Prompt container name
     - Prompt "Load PostgreSQL config?" → accept file path (if not `--config`)
     - Parse config if provided
     - Prompt "Network binding?" → options: localhost (default), or specific IP from local network
       - If specific IP: 
         - Auto-detect user's local network IPs and LAN gateway; offer menu of valid IPs
         - If user enters custom IP: validate it against LAN gateway
           - Extract subnet from gateway (e.g., 192.168.1.0/24)
           - Check if provided IP is on same subnet
           - If invalid: alert "⚠️ Warning: IP 192.168.2.100 is not on your LAN (gateway: 192.168.1.1). You may not be able to access the container. Continue? (y/n)"
           - Allow user to override or select from detected IPs
       - If localhost: container accessible only on 127.0.0.1:5432
     - Build & run container via Docker
     - Create `tsdbadmin` user as superuser (same privileges as postgres)
     - **Display connection info** (host, port, users, connection command)
   
   - If `--list` flag or user chooses "list":
     - Display all containers with status (running/stopped)
     - Prompt action: start, stop, logs, or remove a container
   
   - If `--logs` flag or user chooses "logs":
     - Prompt container name (if not provided)
     - Display logs
   
   - If `--remove` flag or user chooses "remove":
     - Prompt container name (if not provided)
     - Confirm removal
     - Delete from Docker & JSON state

4. **Update State**
   - On any container access, update `last_accessed_at` in JSON

### Design Decisions
- **Always ask new-vs-existing** to prevent orphaned containers
- **Flags for automation:** users can provide `--postgres`, `--timescaledb`, `--config`, `--name` to skip prompts
- **Clear error messages:** version incompatibility, Docker issues, file parse errors
- **Non-invasive config:** config loading is optional; CLI works without it

---

## 5. Docker Integration

### Container Creation
- Use `docker` Python SDK
- Minimal Dockerfile: PostgreSQL + TimescaleDB extension
- Mount PostgreSQL config if provided: `/etc/postgresql/postgresql.conf`
- Pass environment variables for simple KV config settings
- Network mode: bridge with IP binding
  - If localhost binding (127.0.0.1): container accessible only locally
  - If network IP binding (e.g., 192.168.1.100): accessible from other machines on network
- Port mapping: expose container port 5432 to specified IP and port
- Logs output to `./tsdbenv_logs/<container_name>/`
- Create `tsdbadmin` user with same privileges as `postgres` user (superuser)
- On successful creation/update, display connection info to user:
  ```
  ✅ Container 'mydb' created successfully!
  
  Connection Info:
  - Host: 192.168.1.100 (or localhost if local binding)
  - Port: 5432 (or mapped port if custom)
  - Admin User: postgres
  - App User: tsdbadmin (same privileges as postgres)
  - Password: [auto-generated or user-provided]
  
  Connect:
    psql -h 192.168.1.100 -U tsdbadmin -d postgres
  ```

### Operations
- `start(container_name)` — start stopped container; display connection info on start
- `stop(container_name)` — graceful stop
- `remove(container_name)` — delete container & data
- `list()` — return all containers (running + stopped) with connection details
- `get_logs(container_name)` — tail/stream logs

### Error Handling
- Docker daemon not running → check and suggest starting it
- Invalid image → suggest pulling it
- Port conflicts → suggest remapping or removing conflicting container
- Build failures → display Docker build output to user
- User creation failures → log error, offer to retry or use default postgres user

---

## 6. State Tracking & Stale Detection

### State File
Location: `~/.tsdbenv/containers.json`

```json
{
  "containers": [
    {
      "name": "mydb",
      "postgres_version": "14",
      "timescaledb_version": "2.8.0",
      "created_at": "2026-08-19T10:30:00Z",
      "last_accessed_at": "2026-08-19T14:15:00Z",
      "docker_id": "abc123def456",
      "config_path": null,
      "port": 5432,
      "bind_ip": "192.168.1.100",
      "tsdbadmin_password": "auto_generated_secure_password_here"
    }
  ]
}
```

### Stale Detection
- On CLI startup, load containers from JSON
- For each container: if `now() - last_accessed_at > 5 days`, flag as stale
- Before user action, display prompt: "Container 'olddb' unused 7 days. Remove it? (y/n)"
- On any container access (start, logs, stop): update `last_accessed_at`

### State Operations
- `save_container(Container)` — add/update JSON
- `load_containers() -> list[Container]` — read JSON
- `mark_accessed(container_name)` — update timestamp
- `delete_container(container_name)` — remove from JSON & Docker

**Design Rationale:** Simple JSON storage, no external dependencies, human-readable state. Supports inspection and manual editing if needed.

---

## 7. Version Matrix & Compatibility

### Fetching
- **Source:** https://www.tigerdata.com/docs/get-started/timescaledb-supported-platforms#postgresql-timescaledb-support-matrix
- **On first run or periodic refresh:** fetch HTML, parse table, extract mappings
- **Cache location:** `~/.tsdbenv/version_matrix.json` with timestamp
- **Fallback:** if fetch fails and no cache, provide minimal embedded matrix; warn user to check internet

### Validation
- `VersionManager.is_compatible(postgres_ver, timescaledb_ver) -> bool`
- If incompatible: warn user with reason (e.g., "TimescaleDB 2.10.0 requires PostgreSQL 13+")
- Advanced users can override with `--force` flag (at own risk)

### Matrix Structure
```json
{
  "fetched_at": "2026-08-19T10:00:00Z",
  "matrix": {
    "14": ["2.8.0", "2.9.0", "2.10.0"],
    "15": ["2.9.0", "2.10.0", "2.11.0"],
    ...
  }
}
```

---

## 8. Implementation Phases

### Phase 1: Foundation (All Models & Version Logic)
- Data models: `Container`, `VersionMatrix`, `PostgresConfig`
- `VersionManager`: fetch, cache, validate compatibility
- `ConfigHandler`: parse simple KV and full `.conf` files
- `StateTracker`: load/save JSON, stale detection
- Unit tests for all above

### Phase 2: CLI (Top-Down with Docker Stubs)
- Click-based CLI with prompts
- Implement all user interaction flows
- Stub Docker calls (return mock responses)
- Integration tests with mocked Docker

### Phase 3: Docker Integration
- Implement real Docker SDK calls
- Build containers, manage lifecycle
- Replace stubs in CLI
- Integration tests with real Docker or test containers

### Phase 4: Polish & Refinement
- Enhanced error messages
- Logging setup (file + console)
- Performance optimization if needed
- End-to-end testing

---

## 9. Testing Strategy

### Unit Tests (`tests/unit/`)
- `test_version_manager.py` — is_compatible(), matrix parsing, fetch logic
- `test_config_handler.py` — parse simple KV, parse `.conf`, validation
- `test_models.py` — serialization, validation
- `test_state_tracker.py` — save/load JSON, stale detection
- **Coverage target:** 80%+ on core modules

### Integration Tests (`tests/integration/`)
- Mock Docker SDK; test create/list/stop/remove workflows
- CLI flow: new container → validate versions → prompts → (stubbed) build
- State file lifecycle: create → access → stale detection

### Testing Tools
- Framework: pytest
- Fixtures: sample containers, version matrices, config files
- Mocking: unittest.mock for Docker SDK, Click's CliRunner for CLI

---

## 10. Technology Stack

**Language:** Python 3.8+

**Core Libraries:**
- `pydantic` — data validation & models
- `click` — CLI with interactive prompts
- `docker` — Docker Python SDK
- `dataclasses` — lightweight model definitions
- `pathlib` — cross-platform path handling
- `json` — state serialization
- `pytest` — testing framework

**Rationale:** Minimal dependencies, strong OO support, pydantic for validation, click for smooth CLI UX.

---

## 11. Code Organization

```
tsdbenv/
├── __init__.py
├── cli.py                    # Entry point, user prompts (Click)
├── version_manager.py        # VersionMatrix, compatibility logic
├── config_handler.py         # PostgresConfig parsing
├── container_manager.py      # Docker lifecycle operations
├── state_tracker.py          # Container state, stale detection
├── docker_utils.py           # Docker SDK wrapper utilities
├── models.py                 # Container, VersionMatrix, PostgresConfig
└── utils.py                  # Helpers (paths, timestamps, etc.)

tests/
├── unit/
│   ├── test_version_manager.py
│   ├── test_config_handler.py
│   ├── test_models.py
│   ├── test_state_tracker.py
│   └── conftest.py           # Fixtures
└── integration/
    ├── test_cli_flows.py
    ├── test_container_lifecycle.py
    └── conftest.py           # Docker mocks, fixtures

docs/
├── superpowers/
│   └── specs/
│       └── 2026-08-19-tsdbenv-architecture-design.md  # This file
```

---

## 12. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| JSON state (not SQLite) | Lightweight, human-readable, no DB overhead for a CLI tool |
| pydantic models | Built-in validation, type hints, serialization support |
| Click for CLI | Intuitive prompts, flag support, well-tested |
| Docker Python SDK (not docker-compose) | Fine-grained control, programmatic access |
| Phase 1 (foundation) first | Unblock testing & CLI design before Docker integration |
| Top-down CLI next | Users see working interface early, Docker calls stubbed |
| Stale detection (5 days) | Balance: catch forgotten containers without being too aggressive |
| Version matrix fetched from TigerData | Authoritative source, single point of truth |

---

## 13. Out of Scope (Phase 1)

- Custom Docker networks (bridge only; can be extended later)
- Postgres extensions beyond TimescaleDB
- Backup/restore workflows
- Multi-machine orchestration
- Web UI (CLI only for now)

---

## 14. Success Criteria

- ✅ User can run `tsdbenv --new` and create a PostgreSQL + TimescaleDB container with version validation
- ✅ On container creation, `tsdbadmin` user created with superuser privileges (same as postgres)
- ✅ Connection info displayed to user after container creation/start (host, port, users, connection command)
- ✅ Network binding: localhost by default, or user selects/enters IP with validation against LAN gateway
- ✅ IP validation alerts user if bind IP is not on same subnet as LAN gateway; offers detected IPs or override
- ✅ Version compatibility matrix fetched and cached; incompatible versions rejected with clear messages
- ✅ Container state tracked in JSON with port, bind_ip, and tsdbadmin password; stale containers (5d+) detected and warned
- ✅ CLI supports both interactive prompts and flags for automation
- ✅ Docker lifecycle operations (start, stop, remove, list, logs) functional; list shows connection details (including bind IP)
- ✅ Logs available at `./tsdbenv_logs/<container_name>/`
- ✅ 80%+ test coverage on core modules
- ✅ Clean, OO code with no external overhead beyond core dependencies

---

**Document Status:** Ready for implementation  
**Next Step:** Invoke `superpowers:writing-plans` to create detailed implementation plan
