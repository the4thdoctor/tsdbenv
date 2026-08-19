# tsdbenv

PostgreSQL + TimescaleDB environment manager via Docker.

## Overview

**tsdbenv** simplifies local PostgreSQL + TimescaleDB development. Provide versions → validate compatibility → build and run isolated Docker containers with persistent state, automatic port assignment, and easy access to logs.

## Installation

### Quick Install (One Command)

```bash
curl https://raw.githubusercontent.com/wagnerbianchijr/tsdbenv/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/wagnerbianchijr/tsdbenv.git
cd tsdbenv
pip install -r requirements.txt
pip install -e .
```

For detailed installation options including Homebrew, see [INSTALL.md](INSTALL.md).

## Quick Start

Create a PostgreSQL 14 + TimescaleDB 2.10.0 container:

```bash
tsdbenv new --postgres 14 --timescaledb 2.10.0 --bind-ip 127.0.0.1
```

Output:
```
✅ Container 'tsdb-abc12345' created successfully!

Connect:
  psql "postgresql://tsdbadmin:aBcD1234eFgH5678@127.0.0.1:5433"
```

Copy and paste the connection string directly.

## Commands

### new
Create a new PostgreSQL + TimescaleDB container.

```bash
tsdbenv new --postgres 14 --timescaledb 2.10.0 --bind-ip 127.0.0.1
```

**Options:**
- `--postgres VERSION` — PostgreSQL version (e.g., 14, 15)
- `--timescaledb VERSION` — TimescaleDB version (e.g., 2.8.0, 2.10.0)
- `--bind-ip IP` — IP to bind container to (default: 127.0.0.1)
- `--port PORT` — PostgreSQL port (auto-detected if not specified)
- `--config PATH` — PostgreSQL config file (optional)
- `--force` — Skip version compatibility check

**Features:**
- Auto-generates unique container names (`tsdb-{timestamp_hash}`)
- Auto-detects first available port (5432, 5433, 5434, ...)
- Validates PostgreSQL × TimescaleDB version compatibility
- Secure password generation (alphanumeric only)
- Creates `tsdbadmin` superuser with default `tsdb` database

### list
List all containers.

```bash
tsdbenv list
```

Output:
```
Name            PG    TS       IP              Port  
-------------------------------------------------------
tsdb-04d30960   14    2.10.0   127.0.0.1       5433  
tsdb-abcd1234   15    2.11.0   127.0.0.1       5434  
```

### logs
Show container logs.

```bash
tsdbenv logs
```

Select container interactively. Shows PostgreSQL startup logs and readiness status.

### remove
Remove a container.

```bash
tsdbenv remove tsdb-04d30960
```

Confirmation required. Gracefully handles containers no longer in Docker.

## Connection

All containers include a `tsdbadmin` superuser with a secure generated password.

**Default database:** `tsdb`  
**Default user:** `tsdbadmin`

Connect using the provided PostgreSQL URI:

```bash
psql "postgresql://tsdbadmin:password@127.0.0.1:5433/tsdb"
```

## Architecture

**Core Layers:**
1. **CLI** — User-facing commands via Click framework
2. **Version Manager** — PostgreSQL × TimescaleDB compatibility validation
3. **Docker Utils** — Python Docker SDK wrapper for container lifecycle
4. **Network Validator** — IP binding and port availability detection
5. **State Tracker** — Local container metadata persistence
6. **Config Handler** — PostgreSQL config parsing and application

**Container Details:**
- Base image: `timescale/timescaledb:latest-pgXX-oss` (official TimescaleDB)
- Networking: Docker bridge mode
- Storage: Anonymous volumes (data lost on removal)
- Health check: PostgreSQL readiness polling

## Development

```bash
# Run tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/unit -v

# Type checking
python -m mypy src

# Code formatting
python -m black src tests

# Linting
python -m flake8 src tests

# Coverage
python -m pytest --cov=src tests
```

## Version Compatibility

PostgreSQL and TimescaleDB versions must be compatible. The tool validates compatibility before creating containers.

Example compatible pairs:
- PostgreSQL 14 + TimescaleDB 2.8.0 ✅
- PostgreSQL 15 + TimescaleDB 2.10.0 ✅
- PostgreSQL 14 + TimescaleDB 2.10.0 ✅

Incompatible pairs are rejected with clear error messages.

## State Management

Container metadata stored in `~/.tsdbenv/containers.json`:

```json
{
  "tsdb-04d30960": {
    "name": "tsdb-04d30960",
    "postgres_version": "14",
    "timescaledb_version": "2.10.0",
    "created_at": "2026-08-19T10:30:45.123456",
    "last_accessed_at": "2026-08-19T10:35:22.654321",
    "docker_id": "abc123...",
    "port": 5433,
    "bind_ip": "127.0.0.1",
    "tsdbadmin_password": "aBcD1234eFgH5678"
  }
}
```

Stale containers (unused 5+ days) trigger alerts on next `list` command.

## License

MIT
