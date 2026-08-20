# tsdbenv

PostgreSQL + TimescaleDB environment manager via Docker. Spin up isolated local database environments with one command.

## Overview

**tsdbenv** simplifies local PostgreSQL + TimescaleDB development by automating container setup. Provide versions → validate compatibility → build and run isolated Docker containers with persistent state, automatic port assignment, and easy access to logs. Includes all Tiger Cloud extensions (TimescaleDB, pgvector, postgres_fdw, and more).

## Requirements

- **Docker** (installed and running) or **Podman** (rootless mode)
- **Python 3.8+**
- **PostgreSQL 18+** (containers, not host)
- **TimescaleDB 2.29.0+** (containers, not host)
- **Git** (for installer script)

## Installation

### Quick Install (One Command)

```bash
curl https://raw.githubusercontent.com/wagnerbianchijr/tsdbenv/main/install.sh | bash
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
Container 'tsdb-abc12345' created successfully!

Connect:
  psql "postgresql://tsdbadmin:aBcD1234eFgH5678@127.0.0.1:5433"
```

Copy and paste the connection string directly.

## Container Engine Selection

By default, tsdbenv uses Docker. To use Podman instead, specify `--engine podman`:

```bash
tsdbenv -n --engine podman --postgres 15 --timescaledb 2.10.0
```

Set via environment variable to avoid repeating the flag:

```bash
export TSDBENV_ENGINE=podman
tsdbenv -n --postgres 15 --timescaledb 2.10.0
```

**Requirements**: Podman must be installed and configured in rootless mode. Rootless Podman uses slirp4netns for port binding, which may add slight latency compared to Docker's host bridge mode. For setup and network details, see [docs/PODMAN.md](docs/PODMAN.md).

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
- `--init PATH` — SQL file to execute after container creation
- `--tablespaces NAMES` — Comma-separated tablespace names to create
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
tsdbenv -r tsdb-04d30960
```

Confirmation required. Gracefully handles containers no longer in Docker.

### removeall
Remove all containers at once.

```bash
tsdbenv removeall
tsdbenv -a
```

Lists all containers and prompts for confirmation before removing. Useful for cleaning up after testing.

**Options:**
- `--force` — Skip confirmation prompt (dangerous, use with care)

```bash
# With confirmation (default)
tsdbenv -a

# Skip confirmation (requires --force)
tsdbenv removeall --force
```

### connectstring
Get psql command for a container.

```bash
tsdbenv connectstring tsdb-04d30960
```

Outputs ready-to-use psql connection command with embedded password.

### versionrefresh
Refresh TimescaleDB version compatibility matrix.

```bash
tsdbenv versionrefresh
```

Fetches latest compatibility data from Docker Hub, merges with fallback versions, caches locally. Runs automatically on `tsdbenv new`.

### matrix
Display PostgreSQL × TimescaleDB compatibility matrix as a formatted table.

```bash
tsdbenv matrix
```

Shows all supported PostgreSQL versions and their compatible TimescaleDB versions.

## Short Flags

All commands support dash-prefixed short flags for quick access:

```bash
tsdbenv -n --postgres 15 --timescaledb 2.10.0    # new
tsdbenv -l                                        # list
tsdbenv -r tsdb-04d30960                          # remove
tsdbenv -c tsdb-04d30960                          # connectstring
tsdbenv -a                                        # removeall (with confirmation)
tsdbenv -g                                        # versionrefresh (get versions)
tsdbenv -m                                        # matrix
tsdbenv -v                                        # version
tsdbenv -h                                        # help
tsdbenv -t "fast,archive"                         # tablespaces
```

**Combine multiple options:**

```bash
tsdbenv -n --postgres 16 \
  --timescaledb 2.29.2 \
  -t "fast,archive" \
  --init schema.sql
```

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

## Schema Preloading

Automatically load SQL schemas, fixtures, and sample data when creating containers.

**Create a schema file (schema.sql):**

```sql
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    host TEXT NOT NULL,
    cpu FLOAT NOT NULL,
    memory INT NOT NULL
);

SELECT create_hypertable('metrics', 'time');

-- Insert sample data
INSERT INTO metrics VALUES
    (NOW(), 'server-1', 45.2, 2048),
    (NOW(), 'server-2', 62.1, 4096),
    (NOW(), 'server-3', 28.9, 1024);
```

**Create container with schema:**

```bash
tsdbenv -n --postgres 15 --timescaledb 2.10.0 --init schema.sql
```

**Use cases:**
- Load test schemas for integration testing
- Seed sample data for development
- Reproducible test environments
- Regression testing across PostgreSQL versions

## Tablespaces

Create and use custom tablespaces automatically during container creation.

**Automatic tablespace creation:**

```bash
# Create container with multiple tablespaces
tsdbenv -n --postgres 16 --timescaledb 2.29.2 --tablespaces "fast,archive,cold"

# Short flag
tsdbenv -n --postgres 16 --tablespaces "hot,warm,cold"
tsdbenv -n --postgres 16 -t "hot,warm,cold"
```

**Use tablespaces for performance testing:**

```bash
# Connect to container
psql "postgresql://tsdbadmin:password@127.0.0.1:5433/tsdb"

# Create table on specific tablespace
CREATE TABLE metrics_fast (
    time TIMESTAMPTZ,
    data FLOAT
) TABLESPACE fast;

SELECT create_hypertable('metrics_fast', 'time');

# List tablespaces
\db
```

**Features:**
- Automatic directory creation with proper permissions
- Full PostgreSQL integration (ready to use immediately)
- No manual `docker exec` or `chown` commands needed
- Perfect for testing storage performance characteristics

**Note:** Tablespaces are ephemeral — data is lost when the container stops. For persistent tablespaces, use a bind-mounted volume on the host.

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

## License

MIT
