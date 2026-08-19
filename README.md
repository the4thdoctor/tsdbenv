# tsdbenv

PostgreSQL + TimescaleDB environment manager via Docker. Spin up isolated local database environments with one command.

## Overview

**tsdbenv** simplifies local PostgreSQL + TimescaleDB development by automating container setup. Provide versions → validate compatibility → build and run isolated Docker containers with persistent state, automatic port assignment, and easy access to logs. Includes all Tiger Cloud extensions (TimescaleDB, pgvector, postgres_fdw, and more).

## Requirements

- **Docker** (installed and running)
- **Python 3.8+**
- **Git** (for installer script)

## Installation

### Quick Install (Recommended)

```bash
git clone https://github.com/wagnerbianchijr/tsdbenv.git
cd tsdbenv
chmod +x install.sh
./install.sh
```

### Manual Install

```bash
git clone https://github.com/wagnerbianchijr/tsdbenv.git
cd tsdbenv
python3 -m venv venv
source venv/bin/activate
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
Name            PG    TSDB       IP              Port  
---------------------------------------------------------
tsdb-04d30960   14    2.10.0     127.0.0.1       5433  
tsdb-abcd1234   15    2.11.0     127.0.0.1       5434  
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

## Extensions

Containers include Tiger Cloud production extensions pre-installed and enabled:

- **timescaledb** — Time-series data, hypertables, continuous aggregates
- **vector** (pgvector) — Vector similarity search (AI/ML)
- **postgres_fdw** — Foreign data wrapper for remote PostgreSQL connections
- **pg_buffercache** — Buffer pool analysis and statistics
- **pg_stat_statements** — Query performance tracking
- **timescaledb_toolkit** — Advanced time-series analytics functions
- **plpgsql** — PL/pgSQL procedural language

List extensions in container:

```bash
psql "postgresql://tsdbadmin:password@127.0.0.1:5433/tsdb" -c "\dx"
```

## Examples

### Create and connect to a container

```bash
# Create PostgreSQL 15 + TimescaleDB 2.10.0
tsdbenv new --postgres 15 --timescaledb 2.10.0 --bind-ip 127.0.0.1

# Copy the connection string from output
psql "postgresql://tsdbadmin:ABC123def456@127.0.0.1:5433/tsdb"

# Create a hypertable
CREATE TABLE metrics (
  time TIMESTAMPTZ NOT NULL,
  host TEXT NOT NULL,
  cpu FLOAT NOT NULL
);

SELECT create_hypertable('metrics', 'time');
```

### List all running containers

```bash
tsdbenv list

# Output:
# Name            PG    TSDB       IP              Port  
# ---------------------------------------------------------
# tsdb-04d30960   14    2.10.0     127.0.0.1       5433
# tsdb-b1a6b5e5   15    2.10.0     127.0.0.1       5435
```

### View container logs

```bash
tsdbenv logs

# Select container interactively
# Shows PostgreSQL startup logs and readiness status
```

### Remove a container

```bash
tsdbenv remove tsdb-04d30960

# Prompts for confirmation before removal
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

## Troubleshooting

### "Docker is not installed or not running"

```bash
# Install Docker
brew install docker

# Start Docker (macOS)
open /Applications/Docker.app

# Or use Docker Desktop from https://www.docker.com/products/docker-desktop
```

### "Port already in use"

tsdbenv automatically finds the next available port (5432, 5433, 5434, ...). If you need a specific port:

```bash
tsdbenv new --postgres 14 --timescaledb 2.10.0 --port 5440 --bind-ip 127.0.0.1
```

### "Python 3 is required"

```bash
# Install Python
brew install python@3.11

# Verify
python3 --version
```

### Cannot connect to container

Verify the container is running and the connection string is correct:

```bash
tsdbenv list              # Check if container exists
docker ps                 # Check Docker daemon
psql --version            # Check psql is installed
```

### "Version not compatible"

TimescaleDB versions must be compatible with PostgreSQL. Use `--force` to override (not recommended):

```bash
tsdbenv new --postgres 14 --timescaledb 2.11.0 --force --bind-ip 127.0.0.1
```

For compatible versions, see [Version Compatibility](#version-compatibility).

## Contributing

Contributions welcome! 

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make changes and add tests
4. Run test suite: `python -m pytest tests/`
5. Ensure coverage: `python -m pytest --cov=src tests`
6. Format code: `python -m black src tests`
7. Lint: `python -m flake8 src tests`
8. Commit with clear message
9. Push and create a Pull Request

### Development Setup

```bash
git clone https://github.com/wagnerbianchijr/tsdbenv.git
cd tsdbenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
python -m pytest tests/
```

### Running Tests

```bash
# All tests
python -m pytest tests/

# Specific suite
python -m pytest tests/unit -v

# With coverage
python -m pytest --cov=src tests/
```

## License

MIT
