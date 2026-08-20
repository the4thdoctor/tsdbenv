# Podman Support

tsdbenv supports both Docker and Podman as container engines. This guide explains Podman setup, network modes, troubleshooting, and usage.

## Quick Start

Use Podman instead of Docker with a single flag:

```bash
tsdbenv -n --engine podman --postgres 15 --timescaledb 2.10.0
```

Or set the environment variable once:

```bash
export TSDBENV_ENGINE=podman
tsdbenv -n --postgres 15 --timescaledb 2.10.0
```

## Podman Installation

### macOS

Install via Homebrew:

```bash
brew install podman
```

Initialize the Podman machine (required once):

```bash
podman machine init
podman machine start
```

Verify installation:

```bash
podman --version
podman run --rm hello-world
```

### Linux

Most distributions include Podman in their package managers:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install podman
```

**Fedora:**
```bash
sudo dnf install podman
```

**Verify installation:**
```bash
podman --version
podman run --rm hello-world
```

## Rootless Mode Setup

tsdbenv requires rootless Podman. Rootless mode runs containers without root privileges, improving security.

### Enable Rootless Mode

**macOS:** Podman machines are rootless by default. Verify:

```bash
podman info | grep "rootless"
# Output: rootless: true
```

**Linux:** Configure rootless mode:

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install -y uidmap slirp4netns

# Enable user namespaces
echo "user.max_user_namespaces=28633" | sudo tee /etc/sysctl.d/99-podman.conf
sudo sysctl -p /etc/sysctl.d/99-podman.conf

# Initialize rootless Podman
podman system migrate
podman machine init  # On some systems

# Start the Podman socket
systemctl --user start podman.socket
systemctl --user enable podman.socket
```

Verify rootless setup:

```bash
podman info | grep "rootless"
# Output: rootless: true
```

## Network Mode: slirp4netns

Rootless Podman uses **slirp4netns** for user-mode networking. This is a transparent implementation detail:

- **What it is**: User-space network stack that bridges container network traffic without requiring root
- **Why needed**: Rootless containers cannot directly access the host network interface
- **Performance**: Slight latency (typically <1ms per network roundtrip) vs. Docker's kernel bridge mode
- **Transparency**: Port binding works identically to Docker from the user's perspective

### Performance Characteristics

slirp4netns is suitable for local development and testing. For workloads sensitive to network latency, consider:

1. Running Podman in rootful mode (requires `sudo`, less secure)
2. Using Docker (which uses kernel bridge mode for root containers)
3. Testing network-sensitive code with rootful containers in CI/production

### Port Binding Behavior

Port binding in rootless Podman with slirp4netns works as expected:

```bash
# Container port 5432 binds to host port 5433
tsdbenv -n --engine podman --postgres 15 --timescaledb 2.10.0

# Connect using the bound port
psql "postgresql://tsdbadmin:password@127.0.0.1:5433/tsdb"
```

## Usage Examples

### Create a container with Podman

```bash
tsdbenv -n --engine podman --postgres 15 --timescaledb 2.10.0 --bind-ip 127.0.0.1
```

Output:
```
Container 'tsdb-abc12345' created successfully!

Connect:
  psql "postgresql://tsdbadmin:aBcD1234eFgH5678@127.0.0.1:5433"
```

### Use environment variable to default to Podman

```bash
export TSDBENV_ENGINE=podman

# Now all commands use Podman by default
tsdbenv -n --postgres 15 --timescaledb 2.10.0
tsdbenv list
tsdbenv logs
```

### Override default engine on a single command

If `TSDBENV_ENGINE=podman` is set, use Docker for one command:

```bash
export TSDBENV_ENGINE=podman
tsdbenv -n --postgres 15 --timescaledb 2.10.0  # Uses Podman

tsdbenv -n --engine docker --postgres 15 --timescaledb 2.10.0  # Uses Docker
```

### Mix Docker and Podman containers

Manage containers from both engines simultaneously:

```bash
# Create a Docker container
tsdbenv -n --engine docker --postgres 15 --timescaledb 2.10.0

# Create a Podman container
tsdbenv -n --engine podman --postgres 14 --timescaledb 2.10.0

# List shows both (engine is transparent to the user)
tsdbenv list
```

## Troubleshooting

### "Podman is not installed or not running"

**macOS:**
```bash
# Ensure Podman is installed
brew install podman

# Start the Podman machine
podman machine start

# Verify
podman run --rm hello-world
```

**Linux:**
```bash
# Check installation
podman --version

# Start the Podman socket (systemd user session)
systemctl --user start podman.socket
systemctl --user enable podman.socket  # Auto-start on login

# Verify
podman run --rm hello-world
```

### "Socket not found: /var/run/user/{uid}/podman/podman.sock"

Podman's user socket is not running. This typically happens on Linux when the systemd user session isn't started.

**Fix:**

```bash
# Check systemd user session
systemctl --user status podman.socket

# Start it
systemctl --user start podman.socket

# Enable auto-start
systemctl --user enable podman.socket
```

For persistent auto-start across reboots:

```bash
# Ensure user-lingering is enabled
loginctl enable-linger $USER

# Verify
systemctl --user enable podman.socket
```

### "Permission denied" errors

Rootless Podman requires proper user namespace configuration.

**Linux fix:**

```bash
# Check if user namespaces are enabled
cat /etc/sysctl.d/99-podman.conf

# If missing, add it
echo "user.max_user_namespaces=28633" | sudo tee /etc/sysctl.d/99-podman.conf
sudo sysctl -p /etc/sysctl.d/99-podman.conf

# Migrate existing Podman setup
podman system migrate
```

### "Address already in use" for port binding

Port is already occupied by another process.

**Diagnose:**
```bash
# Find process using the port
lsof -i :5433  # macOS
sudo netstat -tulpn | grep 5433  # Linux

# Kill the process (if safe)
kill -9 <PID>
```

**Use a different port:**
```bash
tsdbenv -n --engine podman --postgres 15 --timescaledb 2.10.0 --port 5440 --bind-ip 127.0.0.1
```

### Container works with Docker but fails with Podman

Network namespace issues or missing slirp4netns configuration.

**Verify slirp4netns is installed:**

```bash
# macOS (included with Podman)
podman machine ssh "slirp4netns --version"

# Linux
which slirp4netns
# If missing:
sudo apt-get install slirp4netns  # Ubuntu/Debian
sudo dnf install slirp4netns      # Fedora
```

**Test basic networking:**

```bash
podman run --rm alpine wget -O- http://example.com

# If it hangs, slirp4netns may be misconfigured
```

### macOS Podman machine issues

**Machine won't start:**
```bash
podman machine stop
podman machine rm
podman machine init
podman machine start
```

**Check machine status:**
```bash
podman machine list
podman machine inspect
```

### Performance is slow with slirp4netns

This is expected. Rootless Podman with slirp4netns has inherently higher latency than kernel bridge mode.

**Options:**

1. **Accept the latency** — Suitable for development (typical overhead: <1ms per roundtrip)
2. **Use rootful Podman** — Requires `sudo`, reduces security isolation:
   ```bash
   sudo podman run ...
   ```
3. **Use Docker** — Uses kernel bridge mode, lower latency
4. **Optimize slirp4netns** — Some tuning options available (advanced)

For production testing, rootful containers or Docker are recommended.

## Socket Paths

tsdbenv automatically selects the correct socket for each engine:

| Engine | Socket Path | Platform |
|--------|-------------|----------|
| Docker | `/var/run/docker.sock` | Linux |
| Docker | `/var/run/docker.sock` (via machine) | macOS |
| Podman | `/run/user/{uid}/podman/podman.sock` | Linux (rootless) |
| Podman | `/run/user/{uid}/podman/podman.sock` (via machine) | macOS |

No manual socket configuration needed — tsdbenv handles this automatically.

## Engine Selection Priority

tsdbenv resolves the engine in this order:

1. **CLI flag** — `--engine docker` or `--engine podman` (highest priority)
2. **Environment variable** — `TSDBENV_ENGINE=docker` or `TSDBENV_ENGINE=podman`
3. **Default** — Docker (if neither flag nor env var set)

Example:

```bash
# Uses Docker (CLI flag overrides env var)
export TSDBENV_ENGINE=podman
tsdbenv -n --engine docker --postgres 15 --timescaledb 2.10.0

# Uses Podman (env var fallback)
tsdbenv -n --postgres 15 --timescaledb 2.10.0

# Uses Docker (explicit)
tsdbenv -n --engine docker --postgres 15 --timescaledb 2.10.0
```

## Limitations and Known Issues

### No rootful Podman support for tsdbenv

tsdbenv is designed for rootless Podman only. Rootful mode (running containers as root) reduces security and is not recommended for local development.

### Network latency with slirp4netns

Rootless Podman's user-space networking has inherent latency. Not suitable for latency-sensitive testing, but fine for development.

### Container image availability

Some container images may not be available for Podman if they're specifically built for Docker. tsdbenv uses the official `timescale/timescaledb` image, which works with both engines.

## See Also

- [Podman official documentation](https://docs.podman.io/)
- [slirp4netns GitHub](https://github.com/rootless-containers/slirp4netns)
- [Rootless Podman guide](https://docs.podman.io/en/latest/markdown/podman.1.html#rootless-mode)
- [README.md](../README.md) — General tsdbenv documentation
