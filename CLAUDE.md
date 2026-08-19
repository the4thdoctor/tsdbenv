# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: tsdbenv

tsdbenv manages PostgreSQL + TimescaleDB environments via Docker, handling version compatibility, container lifecycle, and configuration—designed for ease of user interaction.

Repository: https://github.com/wagnerbianchijr/tsdbenv.git

## Development Commands

```bash
# Installation
pip install -r requirements.txt
pip install -e .  # Install package in development mode

# Development & Linting
python -m pytest                    # Run all tests
python -m pytest tests/unit -v      # Run specific test suite
python -m pytest --cov=src          # Run with coverage
python -m black src tests           # Format code
python -m flake8 src tests          # Lint code
python -m mypy src                  # Type checking

# Running tsdbenv
python -m tsdbenv.cli               # Main CLI entry point
```

## Architecture Overview

**Core Concept**: Container-based environment manager for PostgreSQL + TimescaleDB. User provides versions → software validates compatibility → builds and manages Docker containers with persistent state and easy access to logs.

**Phase 3 (Complete)**: Real Docker SDK fully integrated. Containers created via Python Docker SDK, images built from Dockerfile, automatic tsdbadmin user initialization with secure password handling, comprehensive health checks, and complete container lifecycle management.

**Key Design Decisions**:
- Object-oriented Python 3+ throughout
- Follow pgenv model (simple, version-focused)
- Docker bridge networking for container isolation
- Container state tracked locally to warn about unused instances (5+ days)
- User interaction flow: identify container (new or existing) → apply config → build/run
- Real Docker SDK integration for production-grade container operations

**Main Layers**:
1. **CLI/Interface** — User-facing interaction, prompts for version/config selection
2. **Version Manager** — PostgreSQL x TimescaleDB compatibility matrix validation
3. **Container Manager** — Docker lifecycle (create, list, stop, logs)
4. **Configuration Handler** — Parse PostgreSQL configs, apply to container startup
5. **State Tracker** — Track container access times, alert on stale instances

## Directory Structure

```
src/tsdbenv/
├── cli.py                  - Entry point, user interaction prompts
├── version_matrix.py       - PostgreSQL/TimescaleDB compatibility data & validation
├── container_manager.py    - Docker container operations (create, list, logs, stop)
├── config_handler.py       - PostgreSQL config parsing & application
├── state_tracker.py        - Container access tracking & stale detection
├── docker_utils.py         - Docker SDK wrapper utilities
└── models.py               - Data classes for containers, versions, configs

tests/
├── unit/                   - Test individual components
├── integration/            - Test container workflows end-to-end
```

## Critical Implementation Details

**Docker Initialization**:
- On first run, check if Docker daemon is running; prompt user to install/start Docker if missing
- Always use bridge networking mode for containers

**Container Lifecycle**:
- Always ask user: "New container or replace existing?" before any operation to prevent orphaned containers
- Track last-access timestamp for each container
- Alert if container not accessed in 5+ days; offer to terminate

**Version Compatibility**:
- Load PostgreSQL × TimescaleDB compatibility matrix (curated or fetched)
- Validate user-supplied versions; fail with clear explanation if incompatible

**User Interaction Flow**:
1. User runs CLI → ask for PostgreSQL version
2. Ask for TimescaleDB extension version
3. Validate compatibility; alert if problematic
4. Ask: new container or replace existing?
5. Prompt: load PostgreSQL config file? (optional)
6. Build container via Dockerfile/docker-compose
7. Start container with bridge network
8. List available containers; show logs at WORKDIR

**Logging & State**:
- Container logs available at working directory (e.g., `./tsdbenv_logs/<container_name>/`)
- State file tracks containers: name, versions, created date, last accessed, config path

## Key Libraries

- `docker` (Python Docker SDK) — Container management
- `click` — CLI with prompts
- `pydantic` — Data validation & models
- `dataclasses` — Lightweight model definitions
- `pathlib` — Cross-platform path handling
- `json` or `yaml` — State & config serialization

## Important Context

**Requirements**:
- Python 3.8+
- Docker installed and running (checked on first run)
- PostgreSQL & TimescaleDB compatibility data (internal or fetched)

**Compatibility Matrix**:
- Embed or reference a compatibility matrix (e.g., CSV or API) mapping PostgreSQL versions → compatible TimescaleDB versions
- Example: PostgreSQL 14 + TimescaleDB 2.8.0 → compatible; PostgreSQL 13 + TimescaleDB 2.10.0 → incompatible

**Networking**:
- Docker containers use bridge network mode
- User can specify custom network if needed (future enhancement)

**State Persistence**:
- Store container metadata in `~/.tsdbenv/state.json` or project root `.tsdbenv/containers.json`
- Tracks: name, PostgreSQL version, TimescaleDB version, created date, last accessed, config path

## Code Style & Conventions

- **Object-Oriented**: All components are classes (not procedural functions)
- **Best Practices**: Use `__init__.py` with public API exports, type hints throughout, docstrings for classes/methods
- **File Signatures**: Every Python file must include a header signature:
  ```python
  # Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
  # Created: YYYY-MM-DD
  ```
- **Git Commits**: All commits signed as Wagner Bianchi <wagnerbianchijr@gmail.com>

## Testing Strategy

- **Framework**: pytest
- **Structure**: Separate `unit/` and `integration/` test suites
- **Coverage**: Aim for 80%+ coverage on core modules (version validation, container ops)
- **Mocking**: Mock Docker SDK for unit tests; use test containers for integration
- **Patterns**: Fixtures for container state, parametrized tests for version matrix validation

## Common Gotchas

- **Docker not running**: Check daemon status on first run; fail gracefully with installation instructions
- **Orphaned containers**: Always prompt for new vs. replace to prevent leftover containers
- **Stale containers**: Warn user if unused 5+ days; offer cleanup to avoid clutter
- **Config conflicts**: If user loads a PostgreSQL config, validate it doesn't conflict with Docker environment variables
- **Version mismatches**: Always validate PostgreSQL + TimescaleDB combo before building container

---

**When updating CLAUDE.md**:
- Add new user interaction flows as features evolve
- Update version matrix section if compatibility data changes
- Document new libraries added to requirements.txt
- Keep signatures & commit author consistent
