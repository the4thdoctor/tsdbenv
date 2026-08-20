# Phase 3: Real Docker SDK Integration

## Goal

Replace stub implementations with production-grade Docker operations using the Python Docker SDK. Enable real container creation, image building from Dockerfile, automatic user initialization, secure password handling, and complete container lifecycle management.

## Architecture

### Docker SDK Integration

Phase 3 replaces mock Docker operations with real Docker SDK calls via the `docker` Python library. All Docker interactions flow through `docker_utils.py`, which wraps the Docker client and provides a clean, testable interface.

**Docker Client Architecture**:
- Lazy-loaded Docker client instance (first access only)
- Graceful error handling for missing/unavailable Docker daemon
- Support for both Unix socket (Linux/macOS) and Windows named pipes
- Network configuration: bridge networking with custom network support

### Image Building

Containers are built from a `Dockerfile` located at the repository root. The Dockerfile:
- Starts from official PostgreSQL image (version-specific)
- Installs TimescaleDB extension from APT or build source
- Configures PostgreSQL with sensible defaults (listen_addresses, max_connections, shared_buffers)
- Creates init scripts for container startup
- Ensures tsdbadmin user creation during container initialization

**Build Process**:
1. Validate PostgreSQL/TimescaleDB version compatibility
2. Build Docker image with specified versions (tag: `tsdbenv:<pg>-<ts>`)
3. Capture build logs for debugging
4. Verify image exists before container creation

### Container Lifecycle

**Creation**:
1. Check for existing container with same name
2. Create container from built image with:
   - Environment variables for configuration
   - Port mappings (5432 default, customizable)
   - Volume mounts for persistent data and logs
   - Bridge network attachment
3. Generate and inject secure tsdbadmin password
4. Start container with health checks

**Execution**:
- Container runs initialization script on startup
- Script creates tsdbadmin user, sets password, configures PostgreSQL
- Readiness verification via log polling ("database system is ready to accept connections")
- Container logs captured to `./tsdbenv_logs/<container_name>/`

**Cleanup**:
- Stop container: graceful shutdown with timeout
- Remove container: delete from Docker daemon
- Preserve volumes for data retention (optional full cleanup)

## Key Components

### Dockerfile

Located at repository root. Multi-stage build pattern:
- **Stage 1 (Builder)**: Install build dependencies, compile TimescaleDB if needed
- **Stage 2 (Runtime)**: Clean runtime image, copy compiled artifacts, setup PostgreSQL
- **Entrypoint**: Run initialization script, then PostgreSQL

### docker_utils.py

Core Docker operations:
- `DockerClient` class: Lazy-loaded wrapper around `docker.from_env()`
- `build_image()`: Build image from Dockerfile with version tags
- `create_container()`: Create container with network, volumes, environment
- `start_container()`: Start container with health checks
- `stop_container()`: Graceful container shutdown
- `remove_container()`: Remove container from Docker
- `get_container()`: Retrieve running container by name
- `list_containers()`: List all tsdbenv-managed containers
- `get_logs()`: Stream container logs
- `execute_command()`: Run commands inside container (admin operations)

### Container Orchestration

High-level container orchestration (in cli.py and docker_utils.py):
- Version validation, image building, container creation
- Container state and access timestamp management
- User prompts (new vs. replace existing)
- Orphaned container cleanup
- Container listing with metadata

### models.py

Data structures:
- `PostgreSQLVersion`: Version string with validation
- `TimescaleDBVersion`: Version string with validation
- `ContainerConfig`: Configuration object (ports, volumes, environment)
- `ContainerMetadata`: State tracking (created, last accessed, versions)

## Key Features

### Real Container Creation

Containers created via Docker SDK, not mocked. Full production-grade container lifecycle:
- Resource limits (CPU, memory) configurable
- Port mapping with conflict detection
- Volume mounting for persistence
- Health checks for readiness verification

### Password Handling

Secure tsdbadmin password management:
- Generated on container creation (random, 16+ characters)
- Injected via environment variable to init script
- Stored securely in container state file (encrypted option available)
- Never logged or exposed in plain text

### Readiness Verification

Container startup verification via log polling:
- Poll container logs for "database system is ready to accept connections"
- Timeout: 30 seconds maximum wait
- Graceful retry mechanism for transient startup failures
- Provides clear feedback on initialization success

### Image Tagging

Persistent image management:
- Images tagged with PostgreSQL and TimescaleDB versions
- Tag format: `tsdbenv:pg<version>-ts<version>`
- Image reuse: avoid rebuilding same version combo
- Cleanup: optional image pruning for unused versions

### State Tracking

Persistent container metadata:
- State file: `~/.tsdbenv/containers.json` (or project-local `.tsdbenv/containers.json`)
- Tracks: container name, PostgreSQL version, TimescaleDB version, created timestamp, last accessed timestamp, port mapping, volume paths, config file reference
- Stale detection: alerts if container unused 5+ days
- Cleanup workflow: user confirmation before termination

## Testing

### Unit Tests

Located in `tests/unit/`:
- `test_docker_utils.py`: Mock Docker SDK, test all docker_utils functions
- `test_version_manager.py`: Validate version compatibility matrix
- `test_models.py`: Validate data class constraints
- `test_state_tracker.py`: Test state file I/O and stale detection
- `test_config_handler.py`: Test PostgreSQL config parsing
- `test_network_validator.py`: Test network configuration validation
- Mocking strategy: pytest-mock + unittest.mock for Docker SDK

**Mock Strategy**:
- Mock `docker.from_env()` to return controlled client
- Mock image builds to return fake image IDs
- Mock container creation to return fake container objects
- Verify correct Docker SDK methods called with correct arguments

### Integration Tests

Located in `tests/integration/`:
- `test_container_lifecycle.py`: Full end-to-end workflow with real Docker
- `test_docker_real.py`: Build real images, verify container operations
- `test_cli_flows.py`: Test CLI user interaction flows
- Prerequisites: Docker daemon running, at least 2GB free disk space
- Cleanup: All test containers removed after test completion

**Integration Patterns**:
- Fixtures for temporary container state
- Parametrized tests for version matrix (5+ combinations)
- Timeout protection (60 second limit per test)
- Automatic cleanup even on test failure

### Coverage Metrics

**Target**: 80%+ coverage on core modules
- `docker_utils.py`: 85%+ (all Docker operations)
- `version_manager.py`: 90%+ (compatibility validation)
- `models.py`: 88%+ (data validation)
- `config_handler.py`: 75%+ (configuration parsing)
- `state_tracker.py`: 78%+ (state file I/O)
- `network_validator.py`: 85%+ (network configuration)

**Coverage Run**:
```bash
pytest --cov=src --cov-report=html tests/
```

Generates HTML report in `htmlcov/index.html` with per-file and per-function breakdown.

## Implementation Checklist

- [x] Dockerfile complete with PostgreSQL, TimescaleDB, init scripts
- [x] docker_utils.py with full Docker SDK integration
- [x] container_manager.py orchestration
- [x] models.py with validation
- [x] Unit tests for all Docker operations (mocked)
- [x] Integration tests for real container lifecycle
- [x] Password handling (secure generation, injection, storage)
- [x] Health checks (pg_isready, timeout protection)
- [x] State tracking (persistent metadata, stale detection)
- [x] Error handling (Docker daemon missing, image build failure, container conflicts)
- [x] Documentation (this file, inline docstrings)

## Debugging & Troubleshooting

### Docker Daemon Not Running

**Error**: `docker.errors.DockerException: Error while fetching server API version`

**Solution**:
1. Check daemon status: `docker ps`
2. On macOS/Windows: start Docker Desktop
3. On Linux: `sudo systemctl start docker`
4. tsdbenv checks daemon on first run and provides installation guide

### Image Build Failure

**Error**: `docker.errors.BuildError: Build failed with ...`

**Debug**:
1. Check build logs in error message
2. Verify Dockerfile syntax: `docker build --no-cache -f Dockerfile .`
3. Verify PostgreSQL/TimescaleDB version availability
4. Check disk space: `df -h`
5. Review docker_utils.py build_image() function for raw error

### Container Startup Timeout

**Error**: `Container health check failed: pg_isready timeout`

**Debug**:
1. Check container logs: `docker logs <container_name>`
2. Verify port not in use: `lsof -i :5432`
3. Check resource constraints: `docker stats <container_name>`
4. Verify tsdbadmin password was injected correctly
5. Increase health check timeout in docker_utils.py (default 30s)

### Password Not Working

**Error**: `psql: error: FATAL: password authentication failed for user "tsdbadmin"`

**Debug**:
1. Verify password was generated: check container state file
2. Check init script logs: `docker exec <container_name> cat /var/log/tsdbadmin-init.log`
3. Verify environment variable was set: `docker inspect <container_name> | grep TSDBADMIN_PASSWORD`
4. Regenerate password: stop container, update state file, restart

## Future Enhancements

- Custom network support (not just bridge)
- Container resource limits (CPU, memory) user-configurable
- Persistent volume encryption
- Multi-container cluster support (replicas, standby)
- Automated backup and restore
- Metrics collection (Prometheus exporter)
- Container image registry integration

---

**Related Documentation**:
- [Dockerfile](../Dockerfile) — Container image definition
- [docker_utils.py](../src/tsdbenv/docker_utils.py) — Docker SDK wrapper

**Author**: Wagner Bianchi <wagnerbianchijr@gmail.com>
**Created**: 2026-08-19
