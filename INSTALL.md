# Installation Guide

## Quick Install (Recommended)

### Option 1: Installer Script (One Command)

Works on macOS, Linux, and any system with Python, Git, and curl.

```bash
curl https://raw.githubusercontent.com/wagnerbianchijr/tsdbenv/main/install.sh | bash
```

This script:
- Checks for Python 3 and Git
- Clones the repository to `~/.local/share/tsdbenv`
- Creates a virtual environment
- Installs dependencies
- Creates `/usr/local/bin/tsdbenv` symlink
- Ready to use immediately

### Option 2: Homebrew (macOS)

Once the formula is added to Homebrew:

```bash
brew install wagnerbianchijr/tap/tsdbenv
```

Or from local formula:

```bash
brew install ./Formula/tsdbenv.rb
```

### Option 3: Manual Installation

```bash
git clone https://github.com/wagnerbianchijr/tsdbenv.git
cd tsdbenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
tsdbenv --help
```

## Requirements

- **Python 3.8+**
- **Docker** (running)
- **Git** (for installer script)

## Verify Installation

```bash
tsdbenv --version
tsdbenv --help
```

## Quick Start

```bash
tsdbenv new --postgres 14 --timescaledb 2.10.0 --bind-ip 127.0.0.1
```

## Uninstall

### If installed via installer script:

```bash
sudo rm /usr/local/bin/tsdbenv
rm -rf ~/.local/share/tsdbenv
```

### If installed via Homebrew:

```bash
brew uninstall tsdbenv
```

### If installed manually:

```bash
cd tsdbenv
pip uninstall tsdbenv
```

## Troubleshooting

### "Docker is not installed or not running"

```bash
# Install Docker
brew install docker

# Or start Docker Desktop on macOS
open /Applications/Docker.app
```

### "Python 3 is required"

```bash
# Install Python
brew install python@3.11

# Or download from https://www.python.org/downloads/
```

### "Permission denied" when creating symlink

The installer script uses `sudo` to create `/usr/local/bin/tsdbenv`. You may be prompted for your password.

## Publishing to Homebrew

To make `brew install tsdbenv` work:

1. Create a Homebrew tap repository: `homebrew-tap`
2. Add the formula to `homebrew-tap/Formula/tsdbenv.rb`
3. Users can then install with: `brew install wagnerbianchijr/tap/tsdbenv`

Or contribute to [Homebrew Community](https://github.com/Homebrew/homebrew-core) for official distribution.

## Development Installation

```bash
git clone https://github.com/wagnerbianchijr/tsdbenv.git
cd tsdbenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Run tests
python -m pytest tests/
```
